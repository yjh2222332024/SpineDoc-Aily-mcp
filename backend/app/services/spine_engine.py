
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
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

# 🏛️ 架构锚定
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from sqlmodel import select, func, String
from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem, Chunk, ProcessingStatus
from backend.app.core.config import settings
from backend.app.services.parser import hybrid_parser
from backend.app.services.toc.manager import toc_manager
from backend.app.services.toc.aligner import LogicAligner
from backend.app.services.ocr.body_alchemist import BodyAlchemist
from backend.app.services.rag.evidence_harvester import EvidenceHarvester 
from backend.app.services.rag.vector_store import PostgresStore
from backend.app.services.ocr.ocr_process_utils import purge_vram
from backend.app.core.interfaces import IFeishuReporter, NullReporter, IAgenticMemory, NullMemory
from backend.app.infra.loaders.universal_loader import universal_loader

logger = logging.getLogger(__name__)

class SpineEngine:
    def __init__(self, reporter: Optional[IFeishuReporter] = None, memory: Optional[IAgenticMemory] = None):
        self.alchemist = BodyAlchemist()
        self.vector_store = PostgresStore()
        self.harvester = EvidenceHarvester(self.vector_store)
        self._session_maker = get_async_sessionmaker()
        self._git_version_control = None
        self.reporter = reporter or NullReporter()
        self.memory = memory or NullMemory()

    @property
    def git_version_control(self):
        if self._git_version_control is None:
            from backend.app.services.git_services.git_version_control import get_git_version_control
            self._git_version_control = get_git_version_control()
        return self._git_version_control

    async def ingest_document(self,
                              file_path: str,
                              limit_pages: Optional[int] = None,
                              manual_toc_range: Optional[List[int]] = None,
                              manual_offset: Optional[int] = None,
                              force: bool = False,
                              force_ocr: bool = False,
                              force_emergent: bool = False
                              ) -> Dict[str, Any]:
        """🚀 工业级全地形摄入流水线 (V53.1)"""
        p = Path(file_path)
        
        # 1. 格式识别与转换 (Word/LarkDoc -> MD)
        is_pdf = p.suffix.lower() == ".pdf"
        doc_content_md = ""
        
        if not is_pdf:
            print(f"📡 [UniversalLoader] 检测到非 PDF 格式，正在转换: {p.suffix}")
            doc_content_md = await universal_loader.load_to_markdown(file_path)
            file_hash = hashlib.md5(doc_content_md.encode()).hexdigest()
        else:
            with open(str(p), "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()

        # 2. 分流处理
        if not is_pdf:
            return await self._ingest_structured_text(p.name, doc_content_md, file_hash)
        
        # --- 🚀 [PDF Trident Pipeline] ---
        async with self._session_maker() as session:
            # A. 查重
            stmt = select(Document).where(Document.filename == p.name, Document.file_hash == file_hash).order_by(Document.created_at.desc()).limit(1)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing and not force:
                print(f"♻️ [Pipeline] 跳过已存在文档: {file_hash[:8]}")
                return {"id": str(existing.id), "toc": []}
            if existing and force:
                await session.delete(existing); await session.commit()

            # B. 逻辑主权探测
            print(f"🛰️ [Pipeline] Step 1: 逻辑主权探测...")
            is_emergent = force_emergent
            enriched_toc = []
            if not is_emergent:
                meta_toc = []
                try:
                    with fitz.open(str(p)) as doc: meta_toc = doc.get_toc(simple=True)
                except: pass
                if manual_toc_range:
                    enriched_toc = await hybrid_parser.extract_toc_async(str(p), manual_range=manual_toc_range)
                    if not enriched_toc: is_emergent = True
                elif meta_toc and len(meta_toc) > 3:
                    from backend.app.services.toc.base import SpineNode
                    enriched_toc = [SpineNode(id=uuid4(), level=it[0], title=it[1].strip(), logical_page=it[2], source="metadata") for it in meta_toc]
                else:
                    is_emergent = True

            # C. 物理收割 (OCR/Vision)
            is_scanned = LogicAligner.detect_is_scanned([n.model_dump() for n in enriched_toc]) if enriched_toc else False
            need_ocr = force_ocr or is_scanned

            with fitz.open(str(p)) as doc_obj:
                total_pages = min(len(doc_obj), limit_pages) if limit_pages else len(doc_obj)
                offset = manual_offset or 0
                db_doc = Document(id=uuid4(), filename=p.name, file_path=str(p.absolute()),
                                  file_hash=file_hash, status=ProcessingStatus.PROCESSING, 
                                  total_pages=total_pages, is_scanned=need_ocr, page_offset=offset)
                session.add(db_doc); await session.commit(); await session.refresh(db_doc)
                
                if is_emergent:
                    from backend.app.services.toc.emergent_orchestrator import emergent_orchestrator
                    ocr_context = None
                    if need_ocr:
                        _, ocr_context = await self.alchemist.run_full_pipeline(str(p), [], total_pages, limit_pages=limit_pages)
                    refined_chunks, enriched_toc = await emergent_orchestrator.run_full_emergent_pipeline(str(db_doc.id), p.name, doc_obj, ocr_context=ocr_context)
                else:
                    page_markdowns = {}
                    if need_ocr:
                        raw_toc_dicts = [n.model_dump() for n in enriched_toc]
                        _, page_markdowns = await self.alchemist.run_full_pipeline(str(p), raw_toc_dicts, total_pages, limit_pages=limit_pages)
                    enriched_toc = toc_manager.process_raw_toc(enriched_toc, total_pages, forced_offset=offset)
                    from backend.app.services.rag.splitter import structural_splitter
                    raw_segments = []
                    async for seg in structural_splitter.split_by_toc(doc_obj, enriched_toc, ocr_context=page_markdowns if need_ocr else None):
                        raw_segments.append(seg)
                    from backend.app.services.rag.logic_refiner import LogicRefiner
                    refined_chunks = await LogicRefiner(threshold=0.25).refine_batch(p.name, enriched_toc, raw_segments)
                
                purge_vram()
                return await self._finalize_ingestion(db_doc, enriched_toc, refined_chunks)

    async def _ingest_structured_text(self, filename: str, content_md: str, file_hash: str) -> Dict[str, Any]:
        """处理结构化文本（Word/LarkDoc）"""
        from backend.app.services.toc.base import SpineNode
        from backend.app.services.rag.logic_refiner import LogicRefiner
        
        # 1. 简易 TOC 解析 (按 # 层级)
        enriched_toc = []
        lines = content_md.split("\n")
        for line in lines:
            if line.startswith("#"):
                level = line.count("#", 0, line.find(" "))
                if level > 0:
                    enriched_toc.append(SpineNode(id=uuid4(), level=level, title=line.strip("# ").strip(), logical_page=1, source="markdown"))

        # 2. 物理分片与精炼
        segments = [{"content": content_md, "page": 1, "breadcrumb": filename}]
        refined_chunks = await LogicRefiner(threshold=0.25).refine_batch(filename, enriched_toc, segments)

        async with self._session_maker() as session:
            db_doc = Document(id=uuid4(), filename=filename, file_path="virtual_path",
                              file_hash=file_hash, status=ProcessingStatus.PROCESSING, 
                              total_pages=1, is_scanned=False, page_offset=0)
            session.add(db_doc); await session.commit(); await session.refresh(db_doc)
            return await self._finalize_ingestion(db_doc, enriched_toc, refined_chunks)

    async def _finalize_ingestion(self, db_doc: Document, toc: List, chunks: List) -> Dict[str, Any]:
        """统一入库、记忆注入与进化报告"""
        async with self._session_maker() as session:
            # 1. 存入 TOC
            toc_titles = [n.title for n in toc]
            toc_embeddings = await self.vector_store.get_embeddings_api(toc_titles)
            for i, n in enumerate(toc):
                session.add(TocItem(id=n.id, title=n.title, page=n.logical_page, level=n.level, document_id=db_doc.id, embedding=toc_embeddings[i]))
            
            # 2. 存入 Chunks 并触发进化
            all_evolution_logs = []
            for c in chunks:
                chunk_id = UUID(c["id"])
                session.add(Chunk(id=chunk_id, content=c["content"], page_number=c["page_number"], breadcrumb=c["breadcrumb"], 
                                  document_id=db_doc.id, embedding=c["embedding"], logic_tags=c["logic_tags"]))
                
                # 🚀 注入 A-mem 进化系统
                note_id = await self.memory.ingest_memory({"id": str(chunk_id), "content": c["content"], "logic_tags": c["logic_tags"], "document_id": db_doc.id})
                if note_id:
                    logs = await self.memory.evolve_network(note_id)
                    all_evolution_logs.extend(logs)

            db_doc.status = ProcessingStatus.COMPLETED
            await session.commit()

            # 3. 发送进化提醒到飞书
            if all_evolution_logs:
                await self.reporter.sync_asset(
                    {"query": f"Ingest: {db_doc.filename}", "text": f"已完成逻辑蒸馏，识别到 {len(chunks)} 个逻辑点。"},
                    {"evolution_count": len(all_evolution_logs), "details": all_evolution_logs[:5]}
                )
            return {"id": str(db_doc.id), "toc": toc}

    async def hybrid_ask(self, query: str, doc_id: str = "all", chat_id: Optional[str] = None, sync_to_bitable: bool = False) -> List[Dict]:
        """⚖️ 联邦质证接口"""
        from backend.app.services.intelligence.court.federated_court import FederatedCourt
        
        async with self._session_maker() as session:
            court = FederatedCourt(session)
            verdict = await court.hear(query=query, enable_online=True)
            
            # 封装结果
            final_results = [{
                "text": verdict.get("final_answer", "无法生成判决。"),
                "breadcrumb": "🏛️ SpineDoc 联邦判决书",
                "color": verdict.get("color", "YELLOW"),
                "verdict_metadata": {
                    "confidence": verdict.get("confidence", 0.0),
                    "cited_galaxies": verdict.get("cited_galaxies", []),
                    "knowledge_delta": verdict.get("knowledge_delta", {})
                }
            }]
            
            # 触发飞书互动卡片
            target_chat = chat_id or settings.FEISHU_DEFAULT_CHAT_ID
            if target_chat:
                await self.reporter.report_verdict(final_results[0], target_chat)
            
            # 同步 Bitable
            if sync_to_bitable:
                await self.reporter.sync_asset(final_results[0], {})

            return final_results

    def get_chunk_history(self, chunk_id: str, limit: int = 20) -> List[Dict]:
        return self.git_version_control.get_chunk_history(chunk_id, limit)

    def diff_chunks(self, chunk_id: str, old_commit: str, new_commit: str) -> str:
        return self.git_version_control.diff_chunks(chunk_id, old_commit, new_commit)
