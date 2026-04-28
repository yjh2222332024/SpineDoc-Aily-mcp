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
    _check_duplicate_and_commit, split_tiered_to_page_map,
)


class EmergentPdfOrchestrator(BaseIngestOrchestrator):
    """无 TOC 的 PDF —— 涌现管道"""

    def __init__(self, alchemist: BodyAlchemist):
        self.alchemist = alchemist

    async def ingest(
        self, file_path, file_hash, session_maker, engine, ctx=None,
    ):
        ctx = ctx or IngestContext()
        p = Path(file_path)

        # --- 1. 去重探测 ---
        dup = await _check_duplicate_and_commit(
            file_path, file_hash, ctx.force, session_maker,
        )
        if dup:
            print(f"[Pipeline] 跳过已存在文档: {file_hash[:8]}")
            return dup

        need_ocr = ctx.force_ocr

        with fitz.open(str(p)) as doc_obj:
            total_pages = (
                min(len(doc_obj), ctx.limit_pages)
                if ctx.limit_pages
                else len(doc_obj)
            )
            offset = ctx.manual_offset or 0

            # 🚀 [V77.0] 接口化持久化：初始化云端镜像
            from backend.app.services.feishu.bitable_ledger import bitable_ledger
            store = bitable_ledger
            
            doc_record_id = await store.get_or_create_document(
                p.name, file_hash, total_pages, force=ctx.force
            )

            # 2. 物理收割 (Tiered Loading)
            ocr_context = None
            page_text_map = {}
            if need_ocr:
                _, ocr_context = await self.alchemist.run_full_pipeline(
                    str(p), [], total_pages, limit_pages=ctx.limit_pages,
                )
            else:
                md = await TieredPdfLoader().load(file_path)
                page_text_map = split_tiered_to_page_map(md)

            # 3. 原子切分 (Atomic Chunking)
            print(f"📥 [Emergent] 执行全量原子收割...")
            raw_chunks = []
            from backend.app.services.rag.splitter import structural_splitter
            async for chunk in structural_splitter.split_full_document(
                doc_obj, ocr_context=ocr_context, page_text_map=page_text_map
            ):
                chunk["level"] = -1
                raw_chunks.append(chunk)

            # 🚀 [V77.1] 第一阶段：极速搬运 (The Dump)
            print(f"📡 [ShadowSync] 正在将 {len(raw_chunks)} 个正文分片推往云端...")
            await store.save_chunks_batch(doc_record_id, raw_chunks)
            
            # 同时触发影子文档实时渲染 (可选)
            from backend.app.services.feishu.shadow_sync import shadow_sync
            await shadow_sync.init_document(p.name)
            for i in range(0, len(raw_chunks), 20):
                batch = raw_chunks[i:i+20]
                await shadow_sync.push_blocks([{"type": "text", "content": c['content']} for c in batch])

            # 🚀 [V77.2] 第二阶段：云端炼金挂起 (Waiting for Cloud AI)
            # 这是一个关键的挂起点，用户会看到进度轮询
            enriched_data = await store.wait_for_tags(doc_record_id)

            # 🚀 [V77.3] 第三阶段：本地反哺蒸馏 (Late Distillation)
            # 现在我们拿到了带云端标签的数据，开始构建脊梁
            from backend.app.services.toc.latent_distiller import latent_distiller
            import uuid
            synthetic_spine = await latent_distiller.distill_emergent_spine(
                uuid.uuid4(), enriched_data
            )

            # 🚀 [V77.4] 第四阶段：回填与确权 (Retrofit & Finalize)
            print(f"🔗 [Orchestrator] 逻辑主权回填中...")
            
            # 回填目录资产
            if synthetic_spine:
                await store.save_toc_items_batch(doc_record_id, [n.model_dump() for n in synthetic_spine])

            # 触发最终落库逻辑
            from backend.app.core.models import Document
            temp_db_doc = Document(
                id=uuid4(), filename=p.name, file_hash=file_hash,
                total_pages=total_pages
            )
            
            # 注意：此处回填后的 breadcrumb 会更准确
            await _finalize_ingestion(temp_db_doc, synthetic_spine, enriched_data, engine)

            purge_vram()
            print(f"🏁 [Pipeline] 反向涌现流程圆满完成。")

        return {
            "id": doc_record_id,
            "toc": synthetic_spine,
            "bitable_id": doc_record_id
        }

