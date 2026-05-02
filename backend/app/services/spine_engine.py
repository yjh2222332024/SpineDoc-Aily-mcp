"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - "Logic Assassin" Core Engine (Trident Pipeline Edition)
"""
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

from sqlmodel import select, func, String
from backend.app.core.config import settings
from backend.app.services.ocr.body_alchemist import PdfTextExtractor
from backend.app.services.rag.aily_harvester import aily_harvester
from backend.app.core.interfaces import (
    IFeishuReporter, NullReporter, IAgenticMemory, NullMemory,
    IDocumentStore,
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
                 alchemist: Optional[PdfTextExtractor] = None,
                 harvester: Optional[Any] = None,
                 store: Optional[IDocumentStore] = None):
        from backend.app.services.feishu.bitable_ledger import bitable_ledger
        self.alchemist = alchemist or PdfTextExtractor()
        self.harvester = harvester or aily_harvester
        self.store = store or bitable_ledger
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
        """
        Ingest document: Support local files and Feishu cloud URLs.
        """
        is_url = file_path.startswith("http")
        
        # 1. Get content and fingerprint
        if is_url:
            print(f"[CloudLoader] Detecting cloud document link, capturing content...")
            doc_content_md = await universal_loader.load_to_markdown(file_path)
            # Cloud documents use content hash as fingerpint
            file_hash = hashlib.md5(doc_content_md.encode()).hexdigest()
            filename = f"Cloud_{file_hash[:8]}"
            if "docx" in file_path: filename = f"LarkDoc_{file_hash[:8]}"
        else:
            p = Path(file_path)
            filename = p.name
            is_pdf = p.suffix.lower() == ".pdf"
            
            if not is_pdf:
                print(f"[UniversalLoader] Detecting non-PDF local file, executing generic conversion...")
                doc_content_md = await universal_loader.load_to_markdown(file_path)
                file_hash = hashlib.md5(doc_content_md.encode()).hexdigest()
            else:
                with open(str(p), "rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                doc_content_md = None

        # 2. Route to Orchestrator
        ctx = IngestContext(
            force=force, force_ocr=force_ocr,
            limit_pages=limit_pages,
            manual_toc_range=manual_toc_range,
            manual_offset=manual_offset,
            content_md=doc_content_md
        )

        # Local PDF routing
        if not is_url and Path(file_path).suffix.lower() == ".pdf":
            if force_emergent:
                orch = EmergentPdfOrchestrator(self.alchemist, self.store)
            else:
                orch = StandardPdfOrchestrator(self.alchemist, self.store)
            return await orch.ingest(file_path, file_hash, engine=self, ctx=ctx)

        # Generic text / Cloud document routing
        orch = StructuredTextOrchestrator(self.store)
        return await orch.ingest(file_path, file_hash, engine=self, ctx=ctx)

    async def hybrid_ask(self, query: str, doc_id: str = "all",
                         chat_id: Optional[str] = None,
                         enable_online: bool = False,
                         sync_to_bitable: bool = False,
                         return_card: bool = True) -> List[Dict]:
        """
        Retrieval QA: Supports Aily interactive card protocol.
        """
        from backend.app.services.intelligence.retrieval.retrieval_coordinator import (
            RetrievalCoordinator,
        )
        from backend.app.services.intelligence.aily_presenter import aily_presenter

        coordinator = RetrievalCoordinator()
        result = await coordinator.retrieve(query=query, enable_online=enable_online)

        # 1. Construct standard text result
        final_results = [{
            "text": result.get("final_answer", "Unable to generate result."),
            "breadcrumb": "RetrievalCoordinator Result",
            "color": result.get("color", "YELLOW"),
            "result_metadata": {
                "confidence": result.get("confidence", 0.0),
                "cited_sources": result.get("cited_sources", []),
                "knowledge_update": result.get("knowledge_update", {}),
            },
        }]

        # 🚀 [V102.1] Aily white-box enhancement: inject interactive card
        if return_card:
            card_json = aily_presenter.format_result_to_card(result, query)
            final_results[0]["interactive_card"] = card_json

        # 2. Apply knowledge update to Git
        knowledge_update = result.get("knowledge_update", {})
        if knowledge_update and knowledge_update.get("has_delta"):
            from backend.app.services.knowledge.metabolism_manager import get_metabolism_manager
            metabolism = get_metabolism_manager()
            git_results = await metabolism.apply(knowledge_update)
            print(f"[SpineEngine] Applied {len(git_results)} knowledge updates to Git")

        # 3. Ingest new knowledge into A-MEM
        source_results = result.get("source_results", [])
        if source_results and self.memory:
            for src in source_results:
                for chunk in src.get("evidence_chunks", []):
                    await self.memory.ingest_memory({
                        "content": chunk.get("content", ""),
                        "logic_tags": chunk.get("logic_tags", []),
                        "document_id": src.get("doc_id", ""),
                    })

        # 4. Reporting logic
        target_chat = chat_id or settings.FEISHU_DEFAULT_CHAT_ID
        if target_chat:
            await self.reporter.report_result(
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
