from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import fitz

from backend.app.services.toc.emergent_orchestrator import (
    emergent_orchestrator,
)
from backend.app.services.ocr.body_alchemist import BodyAlchemist
from backend.app.services.ocr.ocr_process_utils import purge_vram
from backend.app.core.models import Document, ProcessingStatus
from backend.app.infra.loaders.pdf_tiered_loader import TieredPdfLoader

from . import (
    BaseIngestOrchestrator, IngestContext, _finalize_ingestion,
    split_tiered_to_page_map,
    _compute_embeddings_and_cluster,
)


class EmergentPdfOrchestrator(BaseIngestOrchestrator):
    """PDF without TOC - Emergent Pipeline"""

    def __init__(self, alchemist: BodyAlchemist, store=None):
        from backend.app.services.feishu.bitable_ledger import bitable_ledger
        self.alchemist = alchemist
        self.store = store or bitable_ledger

    async def ingest(
        self, file_path, file_hash, engine, ctx=None, tag_timeout=300,
    ):
        ctx = ctx or IngestContext()
        p = Path(file_path)

        # --- 1. Deduplication (Cloud-Native) ---

        with fitz.open(str(p)) as doc_obj:
            total_pages = (
                min(len(doc_obj), ctx.limit_pages)
                if ctx.limit_pages
                else len(doc_obj)
            )
            offset = ctx.manual_offset or 0

            doc_record_id = await self.store.get_or_create_document(
                p.name, file_hash, total_pages, force=ctx.force
            )

            # 2. Physical Loading
            print(f"[Emergent] Using native text extraction, skipping OCR...")
            ocr_context = None
            md = await TieredPdfLoader().load(file_path)
            page_text_map = split_tiered_to_page_map(md)

            # 3. Atomic Chunking
            print(f"[Emergent] Executing atomic chunking...")
            raw_chunks = []
            from backend.app.services.rag.splitter import structural_splitter
            async for chunk in structural_splitter.split_full_document(
                doc_obj, ocr_context=ocr_context, page_text_map=page_text_map
            ):
                chunk["level"] = -1
                raw_chunks.append(chunk)

            # Phase: Cloud Persistence
            print(f"[Store] Syncing {len(raw_chunks)} chunks to cloud...")
            await self.store.save_chunks_batch(doc_record_id, raw_chunks)

            # Phase: Wait for Enrichment
            enriched_data = await self.store.wait_for_tags(doc_record_id, timeout=tag_timeout)

            # Phase: Late Distillation
            from backend.app.services.toc.latent_distiller import latent_distiller
            import uuid
            synthetic_spine = await latent_distiller.distill_emergent_spine(
                uuid.uuid4(), enriched_data
            )

            # Phase: Retrofit & Backfill
            print(f"[Orchestrator] Backfilling logic sovereignty...")
            
            if synthetic_spine:
                print(f"  ↳ Calculating logic coordinates...")
                from backend.app.services.toc.emergent_orchestrator import emergent_orchestrator
                emergent_orchestrator._backfill_breadcrumbs(enriched_data, synthetic_spine)
                
                for chunk in enriched_data:
                    chunk["doc_rec_id"] = doc_record_id
                await self.store.batch_update_chunks(enriched_data)

                await self.store.save_toc_items_batch(doc_record_id, [n.model_dump() for n in synthetic_spine])

            # Phase: Shadow Sync
            from backend.app.services.feishu.shadow_sync import shadow_sync
            print(f"[ShadowSync] Creating shadow mirror based on synthetic spine...")
            await shadow_sync.init_document(p.name)
            
            blocks = []
            if synthetic_spine:
                sorted_spine = sorted(synthetic_spine, key=lambda x: (x.physical_start, x.level))
                for node in sorted_spine:
                    blocks.append({"type": "heading", "level": abs(node.level), "title": node.title})
                    node_chunks = [c for c in enriched_data if node.physical_start <= c['page_number'] <= node.physical_end]
                    for c in node_chunks:
                        blocks.append({"type": "text", "content": c['content']})
            else:
                blocks = [{"type": "text", "content": c['content']} for c in enriched_data]
            
            for i in range(0, len(blocks), 50):
                await shadow_sync.push_blocks(blocks[i:i+50])

            # Finalize Ingestion
            from backend.app.core.models import Document
            temp_db_doc = Document(
                filename=p.name, file_hash=file_hash,
                total_pages=total_pages
            )
            
            await _finalize_ingestion(temp_db_doc, synthetic_spine, enriched_data, engine, skip_bitable=True)
            await _compute_embeddings_and_cluster(enriched_data, self.store)
            await self.store.update_document_status(doc_record_id, "PROCESSED")

            purge_vram()
            print(f"[Pipeline] Emergent pipeline completed.")

        return {
            "id": doc_record_id,
            "toc": synthetic_spine,
            "bitable_id": doc_record_id
        }

