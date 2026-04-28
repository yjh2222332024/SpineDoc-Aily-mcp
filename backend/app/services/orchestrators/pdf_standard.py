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
from backend.app.services.ocr.body_alchemist import BodyAlchemist
from backend.app.services.ocr.ocr_process_utils import purge_vram
from backend.app.core.models import Document, ProcessingStatus
from backend.app.infra.loaders.pdf_tiered_loader import TieredPdfLoader

from . import (
    BaseIngestOrchestrator, IngestContext, _finalize_ingestion,
    _check_duplicate_and_commit, split_tiered_to_page_map,
)


class StandardPdfOrchestrator(BaseIngestOrchestrator):
    """有 TOC 的 PDF —— 标准管道"""

    def __init__(self, alchemist: BodyAlchemist):
        self.alchemist = alchemist

    async def ingest(
        self, file_path, file_hash, session_maker, engine, ctx=None,
    ):
        ctx = ctx or IngestContext()
        p = Path(file_path)

        # --- 去重 ---
        dup = await _check_duplicate_and_commit(
            file_path, file_hash, ctx.force, session_maker,
        )
        if dup:
            print(f"[Pipeline] 跳过已存在文档: {file_hash[:8]}")
            return dup

        # --- 逻辑主权探测 (HITL 优先) ---
        enriched_toc = []
        meta_toc = []
        try:
            with fitz.open(str(p)) as doc:
                meta_toc = doc.get_toc(simple=True)
        except Exception:
            pass

        if ctx.manual_toc_range:
            print(f"🎯 [HITL] 接收到手动目录范围: P{min(ctx.manual_toc_range)}-P{max(ctx.manual_toc_range)}")
            enriched_toc = await hybrid_parser.extract_toc_async(
                str(p), manual_range=ctx.manual_toc_range,
            )
        elif meta_toc and len(meta_toc) > 3:
            print(f"📡 [Metadata] 发现 PDF 内置书签 ({len(meta_toc)} 条)")
            enriched_toc = [
                SpineNode(
                    id=uuid4(), level=it[0], title=it[1].strip(),
                    logical_page=it[2], source="metadata",
                )
                for it in meta_toc
            ]
        
        if not enriched_toc:
            return await self._fall_through(
                file_path, file_hash, session_maker, engine, ctx,
            )

        # --- 物理/逻辑页码校准 (Offset 对齐) ---
        offset = ctx.manual_offset
        if offset is None:
            # 自动计算 Offset
            raw_toc_dicts = [n.model_dump() for n in enriched_toc]
            offset = LogicAligner.calculate_offset(raw_toc_dicts)
            print(f"⚖️ [Aligner] 自动计算 Offset = {offset}")
        else:
            print(f"⚖️ [HITL] 应用强制 Offset = {offset}")

        with fitz.open(str(p)) as doc_obj:
            # --- 🚀 [V56.0] 物理主权嗅探 ---
            is_scanned = LogicAligner.detect_is_scanned([n.model_dump() for n in enriched_toc])
            need_ocr = ctx.force_ocr or is_scanned
            
            total_pages = (
                min(len(doc_obj), ctx.limit_pages)
                if ctx.limit_pages
                else len(doc_obj)
            )
            offset = ctx.manual_offset or 0

            # 🚀 [V72.0] 接口化持久化：不再直接依赖 Bitable 细节
            from backend.app.services.feishu.bitable_ledger import bitable_ledger
            store: IDocumentStore = bitable_ledger
            
            print(f"🏛️ [ShadowSync] 正在准备云端镜像...")
            doc_record_id = await store.get_or_create_document(
                p.name, file_hash, total_pages, force=ctx.force
            )
            
            # OCR 或三级变速加载
            page_markdowns = {}
            page_text_map = {}
            if need_ocr:
                raw_toc_dicts = [n.model_dump() for n in enriched_toc]
                _, page_markdowns = await self.alchemist.run_full_pipeline(
                    str(p), raw_toc_dicts,
                    total_pages, limit_pages=ctx.limit_pages,
                )
            else:
                md = await TieredPdfLoader().load(file_path)
                page_text_map = split_tiered_to_page_map(md)

            # --- 物理收割与异步编排 ---
            enriched_toc = toc_manager.process_raw_toc(
                enriched_toc, total_pages, forced_offset=offset,
            )
            
            # 🚀 [V72.0] 影子镜像同步 (供飞书文档渲染)
            from backend.app.services.feishu.shadow_sync import shadow_sync
            pushed_headings = set()

            refined_chunks = []

            async for seg in structural_splitter.split_by_toc(
                doc_obj, enriched_toc,
                ocr_context=page_markdowns if need_ocr else None,
                page_text_map=page_text_map or None,
            ):
                # 1. 影子文档渲染同步 (Feishu Doc)
                breadcrumb = seg.get("breadcrumb", "")
                levels = breadcrumb.split(" > ")
                headings_to_push = []
                
                path_track = ""
                for i, title in enumerate(levels):
                    path_track = f"{path_track} > {title}" if path_track else title
                    if path_track not in pushed_headings:
                        headings_to_push.append({"type": "heading", "level": i + 1, "title": title})
                        pushed_headings.add(path_track)
                        
                        # 🚀 [V74.0] 级联审计回归：发现新标题立即同步到 Bitable TOC 记录
                        target_node = next((n for n in enriched_toc if n.title == title), None)
                        if target_node:
                            # 异步触发，不阻塞主解析循环
                            asyncio.create_task(store.save_toc_items_batch(doc_record_id, [target_node.model_dump()]))

                if headings_to_push:
                    await shadow_sync.push_blocks(headings_to_push)
                await shadow_sync.push_blocks([{"type": "text", "content": seg['content']}])

                # 2. 收集分片以供批量落库 (飞书捷径将接管后续打标)
                refined_chunks.append(seg)

            # --- 🚀 [V74.0] 统一批量同步正文：保护 API 频率 ---
            print(f"📡 [Persistence] 正在将 {len(refined_chunks)} 个分片批量同步到 Bitable...")
            await store.save_chunks_batch(doc_record_id, refined_chunks)

            # 3. 触发最终本地落库 (即便你不需要本地，这里也是一个事务终点)
            from backend.app.core.models import Document
            temp_db_doc = Document(
                id=uuid4(), filename=p.name, file_hash=file_hash,
                total_pages=total_pages
            )
            await _finalize_ingestion(temp_db_doc, enriched_toc, refined_chunks, engine)
            
            print(f"🏁 [Pipeline] 收割完成。数据已原子化落库。")
            purge_vram()

            
            print(f"🏁 [Pipeline] 收割完成。")
            purge_vram()

        return {
            "id": doc_record_id, 
            "doc_token": shadow_sync.current_doc_token, 
            "bitable_id": doc_record_id,
            "toc": enriched_toc
        }

    async def _trigger_async_summary(self, doc_rec_id: str, node, content: str):
        """🚀 [V59.0] 豆包 2.0 后台逻辑摘要熔炼"""
        from backend.app.services.feishu.bitable_ledger import bitable_ledger
        from backend.app.services.toc.latent_distiller import latent_distiller
        
        try:
            # 限制输入长度，取精华
            preview = content[:2000]
            summary = await latent_distiller.client.chat.completions.create(
                model=latent_distiller.model,
                messages=[{"role": "user", "content": f"请为以下刑法章节内容生成一段精辟的逻辑摘要（50字以内）：\n{preview}"}]
            )
            node_data = {
                "title": node.title,
                "level": node.level,
                "logical_page": node.logical_page,
                "summary": summary.choices[0].message.content
            }
            await bitable_ledger.save_toc_item(doc_rec_id, node_data)
            print(f"💎 [Summary] 章节 '{node.title}' 摘要熔炼完成并同步。")
        except Exception as e:
            print(f"⚠️ [Summary] 章节摘要同步失败: {e}")

    async def _fall_through(self, file_path, file_hash, session_maker, engine, ctx):
        from .pdf_emergent import EmergentPdfOrchestrator
        orch = EmergentPdfOrchestrator(self.alchemist)
        return await orch.ingest(
            file_path, file_hash, session_maker, engine, ctx,
        )
