"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - "Logic Assassin" Core Engine (Trident Pipeline Edition)
"""
import asyncio
import os
import fitz
import logging
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent  # 跳到项目根目录
sys.path.append(str(project_root))
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4
from pathlib import Path

from sqlmodel import select, func, String
from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem, Chunk, ProcessingStatus
from backend.app.core.config import settings
from backend.app.services.parser import hybrid_parser
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

    async def list_documents(self) -> List[Dict[str, Any]]:
        """获取所有已入库文档"""
        async with self._session_maker() as session:
            stmt = select(Document).order_by(Document.created_at.desc())
            result = await session.execute(stmt)
            docs = result.scalars().all()
            return [{"id": str(d.id), "filename": d.filename, "status": d.status, "total_pages": d.total_pages} for d in docs]

    async def get_document_chunks(self, doc_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """从数据库获取并整理语义切片"""
        async with self._session_maker() as session:
            stmt = select(Document).where(func.cast(Document.id, String).like(f"{doc_id}%")) if len(doc_id) < 36 else select(Document).where(Document.id == UUID(doc_id))
            doc = (await session.execute(stmt)).scalar_one_or_none()
            if not doc: return []
            
            stmt = select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.page_number).limit(limit)
            chunks = (await session.execute(stmt)).scalars().all()
            return [{
                "id": str(c.id), "content": c.content, "page_number": c.page_number,
                "breadcrumb": c.breadcrumb, "keywords": c.logic_tags or [], "logic_tags": c.logic_tags or []
            } for c in chunks]

    async def ingest_document(self,
                              file_path: str,
                              force: bool = False,
                              limit_pages: Optional[int] = None,
                              manual_toc_range: Optional[List[int]] = None,
                              request_api_key: Optional[str] = None,
                              stop_words_path: Optional[str] = None,
                              force_ocr: bool = False,
                              use_font_feature: bool = False,
                              dev_mode: bool = False) -> Dict[str, Any]:
        """🚀 三叉戟解耦流水线 (V43.5 最终加固版)"""
        p = Path(file_path)
        if dev_mode:
            checkpoint_path = f"{file_path}.ocr_cache.json"
            if os.path.exists(checkpoint_path):
                os.remove(checkpoint_path)
                print(f"🔥 [Dev] 已强制删除 Checkpoint")

        async with self._session_maker() as session:
            stmt = select(Document).where(Document.filename == p.name)
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing and not force:
                return {"id": str(existing.id), "toc": []}

            print(f"🛰️ [Pipeline] Step 1: 逻辑脊梁探测与对齐...")
            # 🚀 [V46.5] 这里的 enriched_toc 现在是 List[SpineNode]，自带物理对齐与区间闭合
            enriched_toc = await hybrid_parser.extract_toc_async(
                str(p), manual_range=manual_toc_range, force_ocr=force_ocr, use_font_feature=use_font_feature
            )
            
            with fitz.open(str(p)) as doc_obj:
                total_pages = len(doc_obj)
            
            if limit_pages:
                total_pages = min(total_pages, limit_pages)
                print(f"⚖️ [Limit-Mode] 限制处理前 {total_pages} 页")
            
            # 🚀 [Decoupled] 偏移量已经由 TOCManager 处理，我们只需要记录下来
            offset = enriched_toc[0].physical_start - enriched_toc[0].logical_page if enriched_toc else 0
            is_scanned = LogicAligner.detect_is_scanned([n.model_dump() for n in enriched_toc]) if enriched_toc else False
            need_ocr = force_ocr or (manual_toc_range is not None) or is_scanned

            db_doc = Document(id=uuid4(), filename=p.name, file_path=str(p.absolute()),
                              status=ProcessingStatus.PROCESSING, total_pages=total_pages,
                              is_scanned=need_ocr, page_offset=offset)
            session.add(db_doc); await session.commit(); await session.refresh(db_doc)

            page_markdowns = {}
            if need_ocr:
                print(f"📸 [Pipeline] Step 2: GPU OCR 全量收割...")
                if await get_adaptive_ocr_worker():
                    # 这里保持 raw dict 兼容，或者后续重构 Alchemist
                    raw_toc_dicts = [n.model_dump() for n in enriched_toc]
                    _, page_markdowns = await self.alchemist.run_full_pipeline(str(p), raw_toc_dicts, total_pages, limit_pages=limit_pages)
                    purge_vram()

            # 5. 持久化骨架
            toc_titles = [n.title for n in enriched_toc]
            toc_embeddings = await self.vector_store.get_embeddings_api(toc_titles)
            for i, n in enumerate(enriched_toc):
                session.add(TocItem(id=n.id, title=n.title, page=n.logical_page,
                                    level=n.level, document_id=db_doc.id, 
                                    physical_start=n.physical_start,
                                    physical_end=n.physical_end, 
                                    embedding=toc_embeddings[i]))
            await session.flush()

            # 6. 物理分片
            from backend.app.services.rag.splitter import structural_splitter
            raw_segments = []
            with fitz.open(str(p)) as doc:
                if need_ocr and not manual_toc_range:
                    async for seg in structural_splitter.split_full_document(doc, ocr_context=page_markdowns):
                        raw_segments.append(seg)
                else:
                    async for seg in structural_splitter.split_by_toc(doc, enriched_toc, ocr_context=page_markdowns):
                        raw_segments.append(seg)

            # 7. 逻辑精炼
            from backend.app.services.rag.logic_refiner import LogicRefiner
            print(f"💎 [Pipeline] Step 3: SLM 逻辑精炼...")
            refiner = LogicRefiner(stop_words_path=stop_words_path, api_key=request_api_key)
            refined_chunks = await refiner.refine_batch(p.name, enriched_toc, raw_segments)

            # 8. 入库
            print(f"💾 [Pipeline] Step 4: 知识入库...")
            for i, c in enumerate(refined_chunks):
                session.add(Chunk(id=UUID(c["id"]), content=c["content"], page_number=c["page_number"],
                                  breadcrumb=c["breadcrumb"], document_id=db_doc.id,
                                  embedding=c["embedding"], logic_tags=c["logic_tags"],
                                  metadata_json=c["metadata_json"]))
                if i % 20 == 0: await session.commit()
            
            db_doc.status = ProcessingStatus.COMPLETED
            await session.commit()
            print(f"✅ [Success] {p.name} 入库完成。")
            return {"id": str(db_doc.id), "toc": enriched_toc}

    async def get_document(self, doc_id: str) -> Optional[Dict]:
        async with self._session_maker() as session:
            try:
                stmt = select(Document).where(func.cast(Document.id, String).like(f"{doc_id}%")) if len(doc_id) < 36 else select(Document).where(Document.id == UUID(doc_id))
                doc = (await session.execute(stmt)).scalar_one_or_none()
                if not doc: return None
                t_stmt = select(TocItem).where(TocItem.document_id == doc.id).order_by(TocItem.physical_start)
                tocs = (await session.execute(t_stmt)).scalars().all()
                return {"id": str(doc.id), "filename": doc.filename, "total_pages": doc.total_pages, "status": doc.status, "page_offset": doc.page_offset, "toc": [{"title": t.title, "page": t.page, "p_start": t.physical_start} for t in tocs]}
            except Exception as e: return None

    async def nuke_database(self):
        """☢️ 一键炸库"""
        from sqlalchemy import text
        async with self._session_maker() as session:
            await session.execute(text("TRUNCATE TABLE document RESTART IDENTITY CASCADE"))
            await session.execute(text("TRUNCATE TABLE tocitem RESTART IDENTITY CASCADE"))
            await session.execute(text("TRUNCATE TABLE chunk RESTART IDENTITY CASCADE"))
            await session.commit()
            storage_path = Path(settings.STORAGE_ROOT)
            if storage_path.exists():
                import shutil
                shutil.rmtree(storage_path); storage_path.mkdir(parents=True)
            print("☢️ 数据库与物理存储已清空。")

    async def hybrid_ask(self, query: str, doc_id: str = "all", limit: int = 15, api_key: Optional[str] = None) -> List[Dict]:
        """🚀 联邦/导航双流问答入口"""
        original_key = settings.LLM_API_KEY
        if api_key: settings.LLM_API_KEY = api_key
        try:
            async with self._session_maker() as session:
                stmt = select(Document).where(Document.status == ProcessingStatus.COMPLETED) if doc_id == "all" else select(Document).where((func.cast(Document.id, String).like(f"{doc_id}%")) | (Document.filename.contains(doc_id)))
                docs = (await session.execute(stmt)).scalars().all()
                if not docs: return [{"text": "暂无文档", "page_number": 0, "breadcrumb": "None", "is_verdict": True}]
                
                doc_ids = [str(d.id) for d in docs]
                doc_paths = {str(d.id): d.file_path for d in docs}
                
                from backend.app.services.rag.cascading_retriever import CascadingRetriever
                from spine_cli.core.router import SemanticRouter
                from spine_cli.core.reranker import SpineReranker
                router = SemanticRouter(); reranker = SpineReranker(); cascading_retriever = CascadingRetriever(router=router, reranker=reranker)
                
                tasks = [cascading_retriever.retrieve(query=query, doc_id=d.id, vector_store=self.vector_store, limit=15) for d in docs]
                all_results = await asyncio.gather(*tasks)
                initial_hits = []
                for r in all_results: initial_hits.extend(r)

                # 分流决策：多文档走联邦，单长文档走导航
                if len(docs) > 1 or any(kw in query.lower() for kw in ["对比", "差异", "vs"]):
                    from spine_cli.core.agents.federation.graph import create_federated_graph
                    from spine_cli.core.agents.federation.state import create_initial_state
                    state = create_initial_state(query, doc_ids, doc_paths)
                    state["initial_hits"] = initial_hits
                    res = await create_federated_graph().ainvoke(state)
                    return [{"text": res.get("final_answer", "未达成判决"), "page_number": 0, "breadcrumb": "Chief Justice", "is_verdict": True}]
                else:
                    from spine_cli.core.agents.navigator.graph import create_navigator_graph
                    t_stmt = select(TocItem).where(TocItem.document_id == docs[0].id)
                    t_items = (await session.execute(t_stmt)).scalars().all()
                    tocs = {str(docs[0].id): [{"title": t.title, "page": t.page} for t in t_items]}
                    state = {"query": query, "doc_ids": doc_ids, "doc_paths": doc_paths, "tocs": tocs, "initial_hits": initial_hits, "pro_evidence": [], "con_evidence": [], "final_answer": ""}
                    res = await create_navigator_graph().ainvoke(state)
                    return [{"text": res.get("final_answer", "导航失败"), "page_number": 0, "breadcrumb": "Navigator", "is_verdict": True}]
        finally:
            settings.LLM_API_KEY = original_key
