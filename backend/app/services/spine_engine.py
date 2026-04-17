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
test_file_path = Path(__file__).resolve()
project_root = test_file_path.parent.parent.parent  # 回到 Spine-close 根目录
sys.path.insert(0, str(project_root))
# 当前位置：backend/app/services/spine_engine.py
# 目标位置：Spine-close (根目录)
project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

# 🕸️ [V7.0] 一次性导入所有模型，防止 SQLAlchemy 重复注册错误
import backend.app  # 预先注册所有模型
from sqlmodel import select, func, String
from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem, Chunk, ProcessingStatus
from backend.app.core.config import settings
from backend.app.services.parser import hybrid_parser
from backend.app.services.toc.manager import toc_manager
from backend.app.services.toc.aligner import LogicAligner
from backend.app.services.ocr.body_alchemist import BodyAlchemist
from backend.app.services.rag.evidence_harvester import EvidenceHarvester 
from backend.app.services.rag.vector_store import PostgresStore # 🚀 [V48.6] 迁移至 backend
from backend.app.services.ocr.ocr_process_utils import get_adaptive_ocr_worker, purge_vram
from backend.app.services.intelligence.witness.graph import witness_graph # 🚀 [V3.5] 引入单文档质证大脑

logger = logging.getLogger(__name__)

class SpineEngine:
    def __init__(self):
        self.alchemist = BodyAlchemist()
        self.vector_store = PostgresStore()
        self.harvester = EvidenceHarvester(self.vector_store) # 🚀 [V48.5] 初始化收割机
        self._session_maker = get_async_sessionmaker()
        self._git_version_control = None  # 懒加载

    @property
    def git_version_control(self):
        """📜 Git 版本控制（懒加载）"""
        if self._git_version_control is None:
            from backend.app.services.git_services import get_git_version_control
            self._git_version_control = get_git_version_control()
        return self._git_version_control

    async def ingest_document(self,
                              file_path: str,
                              limit_pages: Optional[int] = None,
                              manual_toc_range: Optional[List[int]] = None,
                              manual_offset: Optional[int] = None,
                              force: bool = False,
                              force_ocr: bool = False,
                              stop_words_path: Optional[str] = None,
                              force_emergent: bool = False # 🚀 [V3.5] 强制逻辑涌现开关
                              ) -> Dict[str, Any]:
        """🚀 三叉戟解耦流水线 (V48.0 确权版)"""
        p = Path(file_path)
        
        # ... (指纹计算逻辑不变)
        with open(str(p), "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()
            
        # ... (查重逻辑不变)
        async with self._session_maker() as session:
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
            # 🚀 [V3.5] 主权判定：逻辑探测
            print(f"🛰️ [Pipeline] Step 1: 逻辑主权探测...")
            
            is_emergent = False
            enriched_toc = []
            
            # A. 如果显式开启了强制涌现，直接跳过探测
            if force_emergent:
                print(f"🔥 [Pipeline] 显式开启【强制涌现】模式，无视一切原生目录。")
                is_emergent = True
                enriched_toc = []
            else:
                # B. 检查 Metadata Outline (原生目录)
                meta_toc = []
                try:
                    with fitz.open(str(p)) as doc:
                        meta_toc = doc.get_toc(simple=True)
                except Exception as e:
                    print(f"⚠️ [Parser] 无法读取 PDF 元数据: {e}")

                if manual_toc_range:
                    # 优先级 1：手动确权，走 VLM 识别 TOC
                    print(f"🎯 [Pipeline] 已指定手动目录范围，进入 VLM 识别模式")
                    is_emergent = False
                    enriched_toc = await hybrid_parser.extract_toc_async(
                        str(p), manual_range=manual_toc_range, force_ocr=False  # TOC 识别不用 OCR
                    )
                    # 🚀 [V50.7] VLM 降级检测：如果返回空 TOC，降级为 Emergent
                    if not enriched_toc:
                        print(f"⚠️ [Pipeline] VLM 提取失败，降级为【Emergent 模式】（正文语义涌现）")
                        is_emergent = True
                elif meta_toc and len(meta_toc) > 3:
                    # 优先级 2：高质量 Metadata，走 Guided
                    print(f"✅ [Metadata] 发现 {len(meta_toc)} 个原生目录项，进入 Guided 模式")
                    is_emergent = False
                    from backend.app.services.toc.base import SpineNode
                    enriched_toc = [SpineNode(
                        id=uuid4(), level=it[0], title=it[1].strip(), 
                        logical_page=it[2], source="metadata"
                    ) for it in meta_toc]
                else:
                    # 优先级 3：逻辑荒原，进入 Emergent
                    print(f"📚 [Pipeline] 无有效引导信息，强制进入 Emergent 模式")
                    is_emergent = True
                    enriched_toc = []

            # 🚀 [V50.8] OCR/TOC 解耦：need_ocr 只由 force_ocr 或扫描件判定决定，与 TOC 来源无关
            is_scanned = LogicAligner.detect_is_scanned([n.model_dump() for n in enriched_toc]) if enriched_toc else False
            need_ocr = force_ocr or is_scanned

            # 🚀 [V3.5] 统一生命周期管理：开启文档对象
            with fitz.open(str(p)) as doc_obj:
                total_pages = len(doc_obj)
                if limit_pages: total_pages = min(total_pages, limit_pages)
                
                # 🚀 [V48.0] 确权 Offset
                offset = manual_offset if manual_offset is not None else 0
                if manual_offset is None and enriched_toc:
                    for node in enriched_toc:
                        if node.physical_start > 0:
                            offset = node.physical_start - node.logical_page
                            break

                # 4. 创建主文档 (在事务中处理)
                db_doc = Document(id=uuid4(), filename=p.name, file_path=str(p.absolute()),
                                  file_hash=file_hash, status=ProcessingStatus.PROCESSING, 
                                  total_pages=total_pages, is_scanned=need_ocr, page_offset=offset)
                session.add(db_doc); await session.commit(); await session.refresh(db_doc)
                
                # 5. 执行收割与蒸馏
                if is_emergent:
                    # --- [模式 C]：逻辑涌现模式 (无 TOC，从正文语义中酿造) ---
                    from backend.app.services.toc.emergent_orchestrator import emergent_orchestrator
                    print(f"🌟 [Pipeline] 正在从正文语义中”酿造”隐性脊梁...")

                    if need_ocr:
                        print(f"📸 [Pipeline] OCR 模式：正文将使用 OCR 提取 (含公式/图表)")
                    else:
                        print(f"📄 [Pipeline] 原生模式：正文将使用 PDF 原生文本")

                    ocr_context = None
                    if need_ocr:
                        print(f"📸 [Pipeline] 执行全量 OCR 收割...")
                        _, ocr_context = await self.alchemist.run_full_pipeline(
                            str(p), [], total_pages, limit_pages=limit_pages
                        )

                    # B. 运行涌现流水线 (此时 doc_obj 依然有效)
                    refined_chunks, enriched_toc = await emergent_orchestrator.run_full_emergent_pipeline(
                        str(db_doc.id), p.name, doc_obj, ocr_context=ocr_context
                    )
                    purge_vram()
                else:
                    # --- [模式 A]：引导模式 (Outline 或 VLM 识别 TOC) ---
                    print(f"🧭 [Pipeline] 进入【引导收割】模式，基于目录主权进行对齐...")
                    if need_ocr:
                        print(f"📸 [Pipeline] OCR 模式：正文将使用 OCR 提取 (含公式/图表)")
                    else:
                        print(f"📄 [Pipeline] 原生模式：正文将使用 PDF 原生文本")

                    skip_pages_list = []
                    if manual_toc_range:
                        if len(manual_toc_range) == 2:
                            skip_pages_list = list(range(manual_toc_range[0], manual_toc_range[1] + 1))
                        else:
                            skip_pages_list = manual_toc_range

                    page_markdowns = {}
                    if need_ocr:
                        print(f"📸 [Pipeline] 正文收割 (跳过目录页：{len(skip_pages_list)})...")
                        raw_toc_dicts = [n.model_dump() for n in enriched_toc]
                        _, page_markdowns = await self.alchemist.run_full_pipeline(
                            str(p), raw_toc_dicts, total_pages,
                            limit_pages=limit_pages,
                            skip_pages=skip_pages_list
                        )
                        purge_vram()

                    # 6. 持久化骨架
                    enriched_toc = toc_manager.process_raw_toc(
                        enriched_toc, total_pages, forced_offset=offset, toc_physical_range=manual_toc_range
                    )
                    
                    # 7. Step 3: 物理分片
                    from backend.app.services.rag.splitter import structural_splitter
                    raw_segments = []
                    async for seg in structural_splitter.split_by_toc(doc_obj, enriched_toc, ocr_context=page_markdowns if need_ocr else None):
                        raw_segments.append(seg)

                    # 8. Step 4: 逻辑精炼
                    from backend.app.services.rag.logic_refiner import LogicRefiner
                    print(f"💎 [Pipeline] Step 3: 语义精炼与指纹注入...")
                    refiner = LogicRefiner(threshold=0.25)
                    refined_chunks = await refiner.refine_batch(p.name, enriched_toc, raw_segments)

            # 9. 统一入库 (此时 doc_obj 已关闭，但数据已在内存就绪)
            print(f"💾 [Pipeline] Step 4: 知识入库 (Mode: {'Emergent' if is_emergent else 'Guided'})...")
            
            # 存入 TocItems
            toc_titles = [n.title for n in enriched_toc]
            toc_embeddings = await self.vector_store.get_embeddings_api(toc_titles)
            for i, n in enumerate(enriched_toc):
                session.add(TocItem(id=n.id, title=n.title, page=n.logical_page,
                                    level=n.level, document_id=db_doc.id, 
                                    physical_start=n.physical_start, physical_end=n.physical_end, 
                                    embedding=toc_embeddings[i], is_synthetic=n.is_synthetic))
            await session.flush()

            # 存入 Chunks
            for i, c in enumerate(refined_chunks):
                session.add(Chunk(id=UUID(c["id"]), content=c["content"], page_number=c["page_number"],
                                  breadcrumb=c["breadcrumb"], document_id=db_doc.id,
                                  embedding=c["embedding"], logic_tags=c["logic_tags"],
                                  metadata_json=c["metadata_json"], level=c.get("level", 1)))
                if i % 20 == 0: await session.commit()
            
            db_doc.status = ProcessingStatus.COMPLETED
            await session.commit()
            print(f"✅ [Success] {p.name} 处理完成。")
            return {"id": str(db_doc.id), "toc": enriched_toc}

    async def list_documents(self) -> List[Dict[str, Any]]:
        """📂 [V48.1] 主权接口：列出所有知识资产"""
        async with self._session_maker() as session:
            stmt = select(Document).order_by(Document.created_at.desc())
            result = await session.execute(stmt)
            docs = result.scalars().all()
            return [{
                "id": str(d.id),
                "filename": d.filename,
                "status": str(d.status),
                "total_pages": d.total_pages,
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat()
            } for d in docs]

    async def get_document(self, doc_id_prefix: str) -> Optional[Dict[str, Any]]:
        """🌳 [V48.1] 主权接口：获取文档详情与逻辑脊梁"""
        async with self._session_maker() as session:
            stmt = select(Document).where(func.cast(Document.id, String).like(f"{doc_id_prefix}%")).limit(1)
            result = await session.execute(stmt)
            doc = result.scalar_one_or_none()
            
            if not doc: return None
            
            stmt_toc = select(TocItem).where(TocItem.document_id == doc.id).order_by(TocItem.page)
            result_toc = await session.execute(stmt_toc)
            toc_items = result_toc.scalars().all()
            
            return {
                "id": str(doc.id),
                "filename": doc.filename,
                "total_pages": doc.total_pages,
                "page_offset": doc.page_offset,
                "toc": [{"title": t.title, "page": t.page, "level": t.level} for t in toc_items]
            }

    async def get_document_chunks(self, doc_id_prefix: str, limit: int = 20) -> List[Dict[str, Any]]:
        """🔍 [V48.1] 主权接口：查看语义切片细节"""
        async with self._session_maker() as session:
            stmt_id = select(Document.id).where(func.cast(Document.id, String).like(f"{doc_id_prefix}%")).limit(1)
            result = await session.execute(stmt_id)
            doc_id = result.scalar_one_or_none()
            
            if not doc_id: return []
            
            stmt_chunks = select(Chunk).where(Chunk.document_id == doc_id).limit(limit)
            result_chunks = await session.execute(stmt_chunks)
            chunks = result_chunks.scalars().all()
            
            return [{
                "id": str(c.id),
                "content": c.content,
                "page_number": c.page_number,
                "breadcrumb": c.breadcrumb,
                "keywords": c.logic_tags or [],
                "logic_tags": c.logic_tags or []
            } for c in chunks]

    async def hybrid_ask(
        self,
        query: str,
        doc_id: str = "all",
        limit: int = 15,
        api_key: Optional[str] = None,
        enable_online: bool = False
    ) -> List[Dict[str, Any]]:
        """⚖️ [V48.1] 联邦质证接口：根据参数路由到单文档证人或联邦法庭"""
        # 路由逻辑：
        # 1. doc_id != "all" AND NOT enable_online → 单文档证人 (witness_graph)
        # 2. 其他情况 → 联邦法庭 (FederatedCourt)

        if doc_id != "all" and not enable_online:
            return await self._single_doc_witness(query, doc_id)
        else:
            return await self._federated_court(query, doc_id, enable_online)

    async def _single_doc_witness(self, query: str, doc_id: str) -> List[Dict[str, Any]]:
        """单文档证人深度质证（无联网，无知识更新）"""
        actual_doc_id = None
        doc_toc = []

        async with self._session_maker() as session:
            # 1. 锁定文档主权
            stmt = select(Document).where(func.cast(Document.id, String).like(f"{doc_id}%")).limit(1)
            res = await session.execute(stmt)
            doc_obj = res.scalar_one_or_none()
            if doc_obj:
                actual_doc_id = str(doc_obj.id)
                # 加载逻辑脊梁 (ISR)
                stmt_toc = select(TocItem).where(TocItem.document_id == doc_obj.id).order_by(TocItem.page)
                res_toc = await session.execute(stmt_toc)
                doc_toc = [{"title": t.title, "page": t.page, "level": t.level, "physical_start": t.physical_start} for t in res_toc.scalars().all()]

        # 2. 构造 WitnessState 初始状态
        initial_state = {
            "query": query,
            "doc_id": actual_doc_id,
            "toc": doc_toc,
            "sub_queries": [],
            "fingerprint_pool": [],
            "selected_ids": [],
            "pro_evidence": [],
            "citation_ids": [],
            "is_sufficient": False,
            "final_answer": ""
        }

        # 3. 运行 Multi-Agent 状态机 (大脑调度层)
        try:
            print(f"🏛️ [Engine] 正在调度单文档证人节点执行深度质证...")
            result_state = await witness_graph.ainvoke(initial_state)

            # 4. 封装结果契约 (兼容 main.py 的显示逻辑)
            final_results = []

            # 第一项必须是主答案
            final_results.append({
                "text": result_state.get("final_answer", "证人拒绝提供证词或质证失败。"),
                "breadcrumb": "🏛️ SpineDoc 联邦判决书",
                "page_number": 0
            })

            # 后续项是物理证据链（带颜色置信度）
            from .intelligence.court.color_confidence import ColorConfidenceCalculator
            color_calc = ColorConfidenceCalculator()

            for evidence in result_state.get("pro_evidence", []):
                # 计算颜色置信度（单文档 PDF 证据）
                chunk_data = {
                    "content": evidence.get("content", ""),
                    "source_url": "",  # 本地 PDF 无外部来源
                    "published_date": None,
                    "query_type": "RESEARCH"
                }
                color, confidence = color_calc.calculate(
                    chunk_data,
                    independent_sources=1,
                    has_conflict=False
                )
                final_results.append({
                    "text": evidence.get("content", ""),
                    "breadcrumb": evidence.get("breadcrumb", "Evidence"),
                    "page_number": evidence.get("page", 0),  # integrator_node 存的是 page
                    "color": color.value,
                    "confidence": confidence
                })

            return final_results

        except Exception as e:
            logger.error(f"❌ [Engine] 调度证人节点失败：{e}")
            import traceback
            traceback.print_exc()
            return [{"text": f"质证流崩溃：{e}", "breadcrumb": "Error", "page_number": 0}]

    async def _federated_court(
        self,
        query: str,
        doc_id: str,
        enable_online: bool
    ) -> List[Dict[str, Any]]:
        """联邦法庭模式（支持联网证据，可能触发知识更新）"""
        from .intelligence.court.federated_court import FederatedCourt

        async with self._session_maker() as session:
            court = FederatedCourt(session)

            # 1. 开庭审理
            verdict = await court.hear(
                query=query,
                limit_per_galaxy=3,
                enable_online=enable_online
            )

            # 2. 封装结果契约
            final_results = []

            # 第一项：主答案
            final_results.append({
                "text": verdict.get("final_answer", "法庭无法生成判决。"),
                "breadcrumb": "🏛️ SpineDoc 联邦判决书",
                "page_number": 0,
                "verdict_metadata": {
                    "confidence": verdict.get("confidence", 0.0),
                    "cited_galaxies": verdict.get("cited_galaxies", []),
                    "knowledge_delta": verdict.get("knowledge_delta", {})
                }
            })

            # 后续项：证据链（带颜色置信度）
            for evidence_package in court.evidence_packages:
                for chunk in evidence_package.get("evidence_chunks", []):
                    final_results.append({
                        "text": chunk.get("content", ""),
                        "breadcrumb": chunk.get("breadcrumb", "Evidence"),
                        "page_number": chunk.get("page_number", 0),
                        "color": chunk.get("color", "YELLOW"),  # 提升到顶层
                        "confidence": chunk.get("confidence", 0.0),  # 提升到顶层
                        "evidence_metadata": {
                            "type": chunk.get("type", "LOCAL_PDF"),
                            "galaxy_name": evidence_package.get("galaxy_name", "Unknown")
                        }
                    })

            return final_results

    # 📜 [V48.7] Git 版本控制方法

    def get_chunk_history(self, chunk_id: str, limit: int = 20) -> List[Dict]:
        """📜 获取 Chunk 的 Git 历史"""
        return self.git_version_control.get_chunk_history(chunk_id, limit)

    def get_chunk_content(
        self,
        chunk_id: str,
        commit_hash: Optional[str] = None
    ) -> Optional[Dict]:
        """📄 获取 Chunk 内容（当前版本或历史版本）"""
        return self.git_version_control.get_chunk_content(chunk_id, commit_hash)

    def revert_chunk(self, chunk_id: str, commit_hash: str) -> bool:
        """♻️ 回滚 Chunk 到指定提交"""
        return self.git_version_control.revert_chunk(chunk_id, commit_hash)

    def diff_chunks(
        self,
        chunk_id: str,
        old_commit: str,
        new_commit: str
    ) -> str:
        """🔍 比较 Chunk 在两个提交之间的差异"""
        return self.git_version_control.diff_chunks(chunk_id, old_commit, new_commit)

    async def apply_knowledge_delta(self, delta: Dict) -> Dict[str, str]:
        """🧬 应用知识增量到 Git"""
        return await self.git_version_control.apply_knowledge_delta(delta)

    # 🌳 [V48.8] TOC 树和切片预览方法

    async def get_document_preview_chunks(self, doc_id: str, limit: int = 5) -> Dict:
        """📇 获取文档前 N 个切片预览数据（JSON 格式）"""
        import json

        doc_info = await self.get_document(doc_id)
        if not doc_info:
            return {"error": "文档不存在"}

        chunks = await self.get_document_chunks(doc_id, limit=limit)
        if not chunks:
            return {"error": "文档没有语义切片", "doc_info": doc_info}

        # 转换为预览格式
        preview_chunks = []
        for chunk in chunks:
            preview_chunk = {
                "id": chunk["id"],
                "page": chunk["page_number"],
                "breadcrumb": chunk["breadcrumb"],
                "keywords": chunk["keywords"][:settings.CONTEXT_CHUNK_PREVIEW_KEYWORDS] if chunk["keywords"] else [],
                "content_preview": chunk["content"][:settings.CONTEXT_CHUNK_PREVIEW_CONTENT] + "..." if len(chunk["content"]) > 200 else chunk["content"]
            }
            preview_chunks.append(preview_chunk)

        return {
            "filename": doc_info["filename"],
            "total_pages": doc_info["total_pages"],
            "preview_count": len(preview_chunks),
            "chunks": preview_chunks
        }

