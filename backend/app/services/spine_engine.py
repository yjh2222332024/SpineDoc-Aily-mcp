"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - "Logic Assassin" Core Engine (Trident Pipeline Edition)
"""
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

from sqlmodel import select, func, String
from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem, Chunk, ProcessingStatus
from backend.app.core.config import settings
from backend.app.services.ocr.body_alchemist import BodyAlchemist
from backend.app.services.rag.evidence_harvester import EvidenceHarvester
from backend.app.services.rag.vector_store import PostgresStore
from backend.app.core.interfaces import (
    IFeishuReporter, NullReporter, IAgenticMemory, NullMemory,
)
from backend.app.infra.loaders.universal_loader import universal_loader
from backend.app.services.orchestrators.base import IngestContext
from backend.app.services.orchestrators.pdf_standard import (
    StandardPdfOrchestrator,
)
from backend.app.services.orchestrators.pdf_emergent import (
    EmergentPdfOrchestrator,
)
from backend.app.services.orchestrators.structured_text import (
    StructuredTextOrchestrator,
)


class SpineEngine:
    def __init__(self,
                 reporter: Optional[IFeishuReporter] = None,
                 memory: Optional[IAgenticMemory] = None,
                 alchemist: Optional[BodyAlchemist] = None,
                 vector_store: Optional[PostgresStore] = None):
        self.alchemist = alchemist or BodyAlchemist()
        self.vector_store = vector_store or PostgresStore()
        self.harvester = EvidenceHarvester(self.vector_store)
        self._session_maker = get_async_sessionmaker()
        self._git_version_control = None
        self.reporter = reporter or NullReporter()
        self.memory = memory or NullMemory()

    @property
    def git_version_control(self):
        if self._git_version_control is None:
            from backend.app.services.git_services.git_version_control import (
                get_git_version_control,
            )
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
        p = Path(file_path)
        is_pdf = p.suffix.lower() == ".pdf"

        # 1. 格式识别与转换
        if not is_pdf:
            print(f"[UniversalLoader] 检测到非 PDF 格式，正在转换: {p.suffix}")
            doc_content_md = await universal_loader.load_to_markdown(file_path)
            file_hash = hashlib.md5(doc_content_md.encode()).hexdigest()
            orch = StructuredTextOrchestrator()
            ctx = IngestContext(force=force, content_md=doc_content_md)
            return await orch.ingest(
                file_path, file_hash,
                session_maker=self._session_maker, engine=self, ctx=ctx,
            )

        with open(str(p), "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

        # 2. 路由到对应管道
        ctx = IngestContext(
            force=force, force_ocr=force_ocr,
            limit_pages=limit_pages,
            manual_toc_range=manual_toc_range,
            manual_offset=manual_offset,
        )
        if force_emergent:
            orch = EmergentPdfOrchestrator(self.alchemist)
        else:
            orch = StandardPdfOrchestrator(self.alchemist)

        return await orch.ingest(
            file_path, file_hash,
            session_maker=self._session_maker, engine=self, ctx=ctx,
        )

    async def hybrid_ask(self, query: str, doc_id: str = "all",
                         chat_id: Optional[str] = None,
                         enable_online: bool = False,
                         sync_to_bitable: bool = False) -> List[Dict]:
        from backend.app.services.intelligence.court.federated_court import (
            FederatedCourt,
        )

        async with self._session_maker() as session:
            court = FederatedCourt(session)
            verdict = await court.hear(query=query, enable_online=enable_online)

            final_results = [{
                "text": verdict.get("final_answer", "无法生成判决。"),
                "breadcrumb": "🏛️ SpineDoc 联邦判决书",
                "color": verdict.get("color", "YELLOW"),
                "verdict_metadata": {
                    "confidence": verdict.get("confidence", 0.0),
                    "cited_galaxies": verdict.get("cited_galaxies", []),
                    "knowledge_delta": verdict.get("knowledge_delta", {}),
                },
            }]

            target_chat = chat_id or settings.FEISHU_DEFAULT_CHAT_ID
            if target_chat:
                await self.reporter.report_verdict(
                    final_results[0], target_chat,
                )

            if sync_to_bitable:
                await self.reporter.sync_asset(final_results[0], {})

            return final_results

    def get_chunk_history(self, chunk_id: str, limit: int = 20) -> List[Dict]:
        return self.git_version_control.get_chunk_history(chunk_id, limit)

    def diff_chunks(self, chunk_id: str, old_commit: str,
                    new_commit: str) -> str:
        return self.git_version_control.diff_chunks(
            chunk_id, old_commit, new_commit,
        )
