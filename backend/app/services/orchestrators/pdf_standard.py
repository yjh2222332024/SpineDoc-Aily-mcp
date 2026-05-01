from __future__ import annotations

from pathlib import Path
from uuid import UUID, uuid4
import asyncio
import re

import fitz

from backend.app.services.rag.splitter import structural_splitter
from backend.app.services.parser import hybrid_parser
from backend.app.services.toc.base import SpineNode
from backend.app.services.toc.manager import toc_manager
from backend.app.services.toc.aligner import LogicAligner
from backend.app.services.ocr.body_alchemist import PdfTextExtractor
from backend.app.services.ocr.ocr_process_utils import purge_vram
from backend.app.core.models import Document, ProcessingStatus
from backend.app.infra.loaders.pdf_tiered_loader import TieredPdfLoader

from . import (
    BaseIngestOrchestrator, IngestContext, _finalize_ingestion,
    _check_duplicate_and_commit, split_tiered_to_page_map,
)


class StandardPdfOrchestrator(BaseIngestOrchestrator):
    """PDF with TOC - Standard Pipeline"""

    def __init__(self, alchemist: PdfTextExtractor, store=None):
        from backend.app.services.feishu.bitable_ledger import bitable_ledger
        self.alchemist = alchemist
        self.store = store or bitable_ledger

    async def ingest(
        self, file_path, file_hash, engine, ctx=None,
    ):
        ctx = ctx or IngestContext()
        p = Path(file_path)

        # --- Deduplication (Cloud-Native) ---
        # Note: _check_duplicate_and_commit now returns None by default as local DB is purged.
        # Cloud-level deduplication is handled by bitable_ledger.get_or_create_document.

        # --- Logic Sovereignty Detection (HITL priority) ---
        enriched_toc = []
        meta_toc = []
        try:
            with fitz.open(str(p)) as doc:
                meta_toc = doc.get_toc(simple=True)
        except Exception:
            pass

        if ctx.manual_toc_range:
            print(f"[HITL] Received manual TOC range: P{min(ctx.manual_toc_range)}-P{max(ctx.manual_toc_range)}")
            enriched_toc = await hybrid_parser.extract_toc_async(
                str(p), manual_range=ctx.manual_toc_range,
            )
        elif meta_toc and len(meta_toc) > 3:
            print(f"[Metadata] Found PDF built-in bookmarks ({len(meta_toc)} items)")
            enriched_toc = [
                SpineNode(
                    id=uuid4(), level=it[0], title=it[1].strip(),
                    logical_page=it[2], source="metadata",
                )
                for it in meta_toc
            ]
        
        if not enriched_toc:
            return await self._fall_through(
                file_path, file_hash, engine, ctx,
            )

        # --- Page Calibration (Offset alignment) ---
        offset = ctx.manual_offset
        if offset is None:
            raw_toc_dicts = [n.model_dump() for n in enriched_toc]
            offset = LogicAligner.calculate_offset(raw_toc_dicts)
            print(f"[Aligner] Automatically calculated Offset = {offset}")
        else:
            print(f"[HITL] Applying manual Offset = {offset}")

        with fitz.open(str(p)) as doc_obj:
            # Physical inspection
            is_scanned = False 
            need_ocr = False
            
            total_pages = (
                min(len(doc_obj), ctx.limit_pages)
                if ctx.limit_pages
                else len(doc_obj)
            )
            offset = ctx.manual_offset or 0

            print(f"[ShadowSync] Preparing cloud mirror...")
            doc_record_id = await self.store.get_or_create_document(
                p.name, file_hash, total_pages, force=ctx.force
            )
            
            page_markdowns = {}
            page_text_map = {}
            md = await TieredPdfLoader().load(file_path)
            page_text_map = split_tiered_to_page_map(md)

            # Processing TOC
            enriched_toc = toc_manager.process_raw_toc(
                enriched_toc, total_pages, forced_offset=offset,
            )
            
            from backend.app.services.feishu.shadow_sync import shadow_sync
            pushed_headings = set()

            refined_chunks = []

            async for seg in structural_splitter.split_by_toc(
                doc_obj, enriched_toc,
                ocr_context=page_markdowns if need_ocr else None,
                page_text_map=page_text_map or None,
            ):
                # 1. Shadow document synchronization (Feishu Doc)
                breadcrumb = seg.get("breadcrumb", "")
                levels = breadcrumb.split(" > ")
                headings_to_push = []
                
                path_track = ""
                for i, title in enumerate(levels):
                    path_track = f"{path_track} > {title}" if path_track else title
                    if path_track not in pushed_headings:
                        headings_to_push.append({"type": "heading", "level": i + 1, "title": title})
                        pushed_headings.add(path_track)
                        
                        target_node = next((n for n in enriched_toc if n.title == title), None)
                        if target_node:
                            # Trigger sync asynchronously
                            asyncio.create_task(self.store.save_toc_items_batch(doc_record_id, [target_node.model_dump()]))

                if headings_to_push:
                    await shadow_sync.push_blocks(headings_to_push)
                await shadow_sync.push_blocks([{"type": "text", "content": seg['content']}])

                # 2. Collect chunks for batch persistence
                refined_chunks.append(seg)

            print(f"[Persistence] Batch syncing {len(refined_chunks)} chunks to store...")
            await self.store.save_chunks_batch(doc_record_id, refined_chunks)

            # 3. Finalize ingestion
            from backend.app.core.models import Document
            temp_db_doc = Document(
                filename=p.name, file_hash=file_hash,
                total_pages=total_pages
            )
            await _finalize_ingestion(temp_db_doc, enriched_toc, refined_chunks, engine, store=self.store)
            
            print(f"[Pipeline] Ingestion completed. Data persisted.")
            purge_vram()

        return {
            "id": doc_record_id, 
            "doc_token": shadow_sync.current_doc_token, 
            "bitable_id": doc_record_id,
            "toc": enriched_toc
        }

    async def _trigger_async_summary(self, doc_rec_id: str, node, content: str):
        """Async summary generation"""
        from backend.app.services.toc.latent_distiller import latent_distiller

        try:
            preview = content[:2000]
            summary = await latent_distiller.client.chat.completions.create(
                model=latent_distiller.model,
                messages=[{"role": "user", "content": f"Generate a concise summary (under 50 words) for the following content:\n{preview}"}]
            )
            node_data = {
                "title": node.title,
                "level": node.level,
                "logical_page": node.logical_page,
                "summary": summary.choices[0].message.content
            }
            await self.store.save_toc_item(doc_rec_id, node_data)
            print(f"[Summary] Chapter '{node.title}' summary generated and synced.")
        except Exception as e:
            print(f"⚠️ [Summary] Chapter summary sync failed: {e}")

    async def _fall_through(self, file_path, file_hash, engine, ctx):
        from .pdf_emergent import EmergentPdfOrchestrator
        orch = EmergentPdfOrchestrator(self.alchemist, self.store)
        return await orch.ingest(
            file_path, file_hash, engine, ctx,
        )
