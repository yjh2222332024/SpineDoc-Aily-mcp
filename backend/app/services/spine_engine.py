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
from backend.app.services.ocr.body_alchemist import BodyAlchemist
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
                 alchemist: Optional[BodyAlchemist] = None,
                 harvester: Optional[Any] = None,
                 store: Optional[IDocumentStore] = None):
        from backend.app.services.feishu.bitable_ledger import bitable_ledger
        self.alchemist = alchemist or BodyAlchemist()
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

    async def ingest(self, 
                     file_path: str, 
                     file_hash: Optional[str] = None, 
                     tag_timeout: int = 300,
                     force: bool = False) -> Dict[str, Any]:
        """
        🚀 [V105.0] 统一确权入口 (Proxy)
        职责：对齐编排脚本的接口契约。
        """
        return await self.ingest_document(
            file_path=file_path,
            tag_timeout=tag_timeout,
            force=force
            # 内部逻辑会自动重新计算或处理 file_hash
        )

    async def ingest_document(self,
                              file_path: str,
                              limit_pages: Optional[int] = None,
                              manual_toc_range: Optional[List[int]] = None,
                              manual_offset: Optional[int] = None,
                              force: bool = False,
                              force_ocr: bool = False,
                              force_emergent: bool = False,
                              tag_timeout: int = 300,
                              ) -> Dict[str, Any]:
        """
        Ingest document: Support local files and Feishu cloud URLs.

        Args:
            tag_timeout: 等待语义标注的超时秒数。30 用于测试，300 用于生产。
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
            return await orch.ingest(file_path, file_hash, engine=self, ctx=ctx,
                                     tag_timeout=tag_timeout)

        # Generic text / Cloud document routing
        orch = StructuredTextOrchestrator(self.store)
        return await orch.ingest(file_path, file_hash, engine=self, ctx=ctx,
                                 tag_timeout=tag_timeout)

    async def hybrid_ask(self, query: str, doc_id: str = "all",
                         chat_id: Optional[str] = None,
                         enable_online: bool = False,
                         sync_to_bitable: bool = False,
                         return_card: bool = True,
                         limit: int = 10,
                         api_key: Optional[str] = None) -> List[Dict]:
        """
        Retrieval QA: Runs LogicCourt full graph (PLAN→HARVEST→AUDIT→SYNTHESIZE→EVOLVE).
        """
        from backend.app.services.intelligence.retrieval.graph.coordinator import logic_court
        from backend.app.services.intelligence.retrieval.graph.adapter import (
            create_initial_court_state,
            adapt_court_state_to_hybrid_output,
        )
        from spine_interaction.cards.builder import LarkCardBuilder

        # Phase 1: Run LogicCourt full graph
        initial_state = create_initial_court_state(query, doc_id=doc_id)
        court_state = await logic_court.run_from_state(initial_state)

        # Phase 2: Adapt CourtState back to callers' expected format
        result = adapt_court_state_to_hybrid_output(court_state)

        # 1. Construct standard text result
        final_results = [{
            "text": result.get("final_answer", "Unable to generate result."),
            "breadcrumb": "LogicCourt Result",
            "color": result.get("color", "YELLOW"),
            "result_metadata": {
                "confidence": result.get("confidence", 0.0),
                "cited_sources": result.get("cited_sources", []),
            },
            "phase_log": result.get("phase_log", []),   # 🚀 [V230.0] 阶段时间线
        }]

        # 🚀 [V210.0] 证据溯源：将证据链追加到结果列表，供 CLI 渲染溯源表格
        evidence_pool = court_state.get("evidence_pool", [])
        seen_ids = set()
        for e in evidence_pool:
            eid = e.get("id", "")
            if eid and eid not in seen_ids:
                seen_ids.add(eid)
                raw_color = e.get("color", "YELLOW")
                # 归一化颜色值：处理 "ConfidenceColor.YELLOW" → "YELLOW"
                if "." in str(raw_color):
                    raw_color = str(raw_color).split(".")[-1]
                claim_text = "; ".join(e.get("claims", []))[:200]
                final_results.append({
                    "text": claim_text or e.get("summary", e.get("content", "[PRUNED]"))[:200],
                    "breadcrumb": e.get("breadcrumb", e.get("origin", "Unknown")),
                    "page_number": e.get("page_number", 0),
                    "color": raw_color,
                    "confidence": e.get("confidence", 0.0),
                    "origin": e.get("origin", "UNKNOWN"),
                })

        # 🚀 [V102.1] Inject interactive card (LarkCardBuilder with phase_log timeline)
        if return_card:
            card_json = LarkCardBuilder().build_result_card(
                final_results[0], query=query,
                evidence_trace=final_results[1:] if len(final_results) > 1 else None,
            )
            final_results[0]["interactive_card"] = card_json

        # 2. Ingest new knowledge into A-MEM
        if self.memory:
            evidence_pool = court_state.get("evidence_pool", [])
            for chunk in evidence_pool:
                await self.memory.ingest_memory({
                    "content": chunk.get("content", ""),
                    "logic_tags": chunk.get("claims", chunk.get("logic_tags", [])),
                    "document_id": chunk.get("doc_id", ""),
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
