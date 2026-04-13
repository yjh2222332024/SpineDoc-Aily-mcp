"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - "Logic Assassin" Core Engine (Trident Pipeline Edition)
"""
import asyncio
import os
import fitz
import logging
import sys
import hashlib
from pathlib import Path

# 🏛️ 顶级架构师：统一路径锚定，防止平行宇宙 import
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

from sqlmodel import select, func, String
from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem, Chunk, ProcessingStatus
from backend.app.core.config import settings
from backend.app.services.parser import hybrid_parser
from backend.app.services.toc.manager import toc_manager
from backend.app.services.toc.aligner import LogicAligner
from backend.app.services.ocr.body_alchemist import BodyAlchemist
from spine_cli.indexer.postgres_store import PostgresStore
from backend.app.services.ocr.ocr_process_utils import get_adaptive_ocr_worker, purge_vram

logger = logging.getLogger(__name__)

class SpineEngine:
    def __init__(self):
        self.alchemist = BodyAlchemist()
        self.vector_store = PostgresStore()
        self._session_maker = get_async_sessionmaker()

    async def ingest_document(self,
                              file_path: str,
                              force: bool = False,
                              limit_pages: Optional[int] = None,
                              manual_toc_range: Optional[List[int]] = None,
                              manual_offset: Optional[int] = None,
                              request_api_key: Optional[str] = None,
                              stop_words_path: Optional[str] = None,
                              force_ocr: bool = False,
                              use_font_feature: bool = False,
                              dev_mode: bool = False) -> Dict[str, Any]:
        """🚀 三叉戟解耦流水线 (V48.0 确权版)"""
        p = Path(file_path)
        
        # 1. 🏛️ 第一性原理：计算文件指纹 (MD5)
        with open(str(p), "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
            
        if dev_mode:
            checkpoint_path = f"{file_path}.ocr_cache.json"
            if os.path.exists(checkpoint_path):
                os.remove(checkpoint_path); print(f"🔥 [Dev] 已清理 Checkpoint")

        async with self._session_maker() as session:
            # 2. 🛡️ 唯一性检查与强制覆盖逻辑
            stmt = select(Document).where(Document.filename == p.name, Document.file_hash == file_hash).order_by(Document.created_at.desc()).limit(1)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                if force:
                    print(f"🗑️ [Pipeline] 检测到强制覆盖指令，正在清理旧版本: {file_hash[:8]}")
                    await session.delete(existing)
                    await session.commit()
                else:
                    print(f"♻️ [Pipeline] 跳过已存在文档: {file_hash[:8]}")
                    return {"id": str(existing.id), "toc": []}

        # 重新开启 Session 处理后续逻辑
        async with self._session_maker() as session:
            # 3. Step 1: 逻辑脊梁探测
            print(f"🛰️ [Pipeline] Step 1: 逻辑脊梁探测与对齐...")
            enriched_toc = await hybrid_parser.extract_toc_async(
                str(p), manual_range=manual_toc_range, force_ocr=force_ocr, use_font_feature=use_font_feature
            )
            
            with fitz.open(str(p)) as doc_obj: total_pages = len(doc_obj)
            if limit_pages: total_pages = min(total_pages, limit_pages)
            
            # 🚀 [V48.0] 确权 Offset：用户输入优先
            if manual_offset is not None:
                offset = manual_offset
                print(f"⚖️ [Pipeline] 使用用户确权 Offset: {offset}")
            else:
                offset = 0
                for node in enriched_toc:
                    if node.physical_start > 0:
                        offset = node.physical_start - node.logical_page
                        break
            
            is_scanned = LogicAligner.detect_is_scanned([n.model_dump() for n in enriched_toc]) if enriched_toc else False
            need_ocr = force_ocr or (manual_toc_range is not None) or is_scanned

            # 4. 创建主文档
            db_doc = Document(id=uuid4(), filename=p.name, file_path=str(p.absolute()),
                              file_hash=file_hash, status=ProcessingStatus.PROCESSING, 
                              total_pages=total_pages, is_scanned=need_ocr, page_offset=offset)
            session.add(db_doc); await session.commit(); await session.refresh(db_doc)
            # 🚀 [V48.2] 原子化修复：展开 TOC 屏蔽区间
            skip_pages_list = []
            if manual_toc_range:
                if len(manual_toc_range) == 2:
                    skip_pages_list = list(range(manual_toc_range[0], manual_toc_range[1] + 1))
                else:
                    skip_pages_list = manual_toc_range

            page_markdowns = {}
            if need_ocr:
                print(f"📸 [Pipeline] Step 2: 正文收割 (Bypass Pages: {len(skip_pages_list)})...")
                raw_toc_dicts = [n.model_dump() for n in enriched_toc]
                # 🚀 [V48.0] 传入展开后的列表
                _, page_markdowns = await self.alchemist.run_full_pipeline(
                    str(p), raw_toc_dicts, total_pages, 
                    limit_pages=limit_pages,
                    skip_pages=skip_pages_list
                )
                purge_vram()

            # 6. 持久化骨架
            # 🚀 [V48.0] 守护者逻辑注入
            enriched_toc = toc_manager.process_raw_toc(
                enriched_toc, total_pages, 
                forced_offset=offset,
                toc_physical_range=manual_toc_range
            )
            
            toc_titles = [n.title for n in enriched_toc]
            toc_embeddings = await self.vector_store.get_embeddings_api(toc_titles)
            for i, n in enumerate(enriched_toc):
                session.add(TocItem(id=n.id, title=n.title, page=n.logical_page,
                                    level=n.level, document_id=db_doc.id, 
                                    physical_start=n.physical_start, physical_end=n.physical_end, 
                                    embedding=toc_embeddings[i]))
            await session.flush()

            # 7. Step 3: 物理分片
            from backend.app.services.rag.splitter import structural_splitter
            raw_segments = []
            with fitz.open(str(p)) as doc:
                ctx = page_markdowns if need_ocr else None
                async for seg in structural_splitter.split_by_toc(doc, enriched_toc, ocr_context=ctx):
                    raw_segments.append(seg)

            # 8. Step 4: 逻辑精炼
            from backend.app.services.rag.logic_refiner import LogicRefiner
            print(f"💎 [Pipeline] Step 3: 语义精炼与指纹注入...")
            refiner = LogicRefiner(threshold=0.25)
            refined_chunks = await refiner.refine_batch(p.name, enriched_toc, raw_segments)

            # 9. 入库
            print(f"💾 [Pipeline] Step 4: 知识入库...")
            for i, c in enumerate(refined_chunks):
                session.add(Chunk(id=UUID(c["id"]), content=c["content"], page_number=c["page_number"],
                                  breadcrumb=c["breadcrumb"], document_id=db_doc.id,
                                  embedding=c["embedding"], logic_tags=c["logic_tags"],
                                  metadata_json=c["metadata_json"]))
                if i % 20 == 0: await session.commit()
            
            db_doc.status = ProcessingStatus.COMPLETED
            await session.commit()
            print(f"✅ [Success] {p.name} 处理完成。")
            return {"id": str(db_doc.id), "toc": enriched_toc}

    async def nuke_database(self):
        from sqlalchemy import text
        async with self._session_maker() as session:
            await session.execute(text("TRUNCATE TABLE document RESTART IDENTITY CASCADE"))
            await session.commit()
            print("☢️ 数据库已清空。")
