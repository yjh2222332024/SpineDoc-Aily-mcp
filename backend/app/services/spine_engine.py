"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - "Logic Assassin" Core Engine (Trident Pipeline Edition)
"""
import hashlib
import time
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
        from backend.app.services.intelligence.retrieval.graph.coordinator import RetrievalGraphOrchestrator
        
        self.alchemist = alchemist or BodyAlchemist()
        self.store = store or bitable_ledger
        self._git_version_control = None
        self.reporter = reporter or NullReporter()
        self.memory = memory or NullMemory()
        
        # [V280.0] 初始化检索图编排器 (DI)
        self.court = RetrievalGraphOrchestrator(memory=self.memory)

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
         [V105.0] 统一确权入口 (Proxy)
        职责：对齐编排脚本的接口契约。
        """
        return await self.ingest_document(
            file_path=file_path,
            tag_timeout=tag_timeout,
            force=force
            # 内部逻辑会自动重新计算或处理 file_hash
        )

    async def _resolve_document_input(self, file_path: str) -> Dict[str, Any]:
        """提取文档输入解析逻辑：URL 检测、哈希计算、内容加载。"""
        is_url = file_path.startswith("http")
        if is_url:
            print(f"[CloudLoader] Detecting cloud document link, capturing content...")
            doc_content_md = await universal_loader.load_to_markdown(file_path)
            file_hash = hashlib.md5(doc_content_md.encode()).hexdigest()
            filename = f"Cloud_{file_hash[:8]}"
            if "docx" in file_path:
                filename = f"LarkDoc_{file_hash[:8]}"
        else:
            p = Path(file_path)
            filename = p.name
            if p.suffix.lower() != ".pdf":
                print(f"[UniversalLoader] Detecting non-PDF local file, executing generic conversion...")
                doc_content_md = await universal_loader.load_to_markdown(file_path)
                file_hash = hashlib.md5(doc_content_md.encode()).hexdigest()
            else:
                with open(str(p), "rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()
                doc_content_md = None
        return {"filename": filename, "file_hash": file_hash, "doc_content_md": doc_content_md, "is_url": is_url}

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
        resolved = await self._resolve_document_input(file_path)
        filename = resolved["filename"]
        file_hash = resolved["file_hash"]
        doc_content_md = resolved["doc_content_md"]
        is_url = resolved["is_url"]

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

    async def plan_investigation(self, query: str, doc_id: str = "all") -> Dict[str, Any]:
        """ [V250.0] Step 1: Planner Phase """
        start = time.time()
        from backend.app.services.intelligence.retrieval.graph.adapter import create_initial_court_state
        from backend.app.services.intelligence.retrieval.constants import RetrievalPhase

        state = create_initial_court_state(query, doc_id=doc_id)
        # 直接调用编排器中注入的节点
        plan_func = self.court.nodes[RetrievalPhase.PLAN]
        result = await plan_func(state)

        return {
            "sub_queries": result.get("sub_queries", []),
            "focus_areas": result.get("focus_areas", []),
            "target_galaxy_ids": result.get("target_galaxy_ids", []),
            "phase_log": [{
                "step": "PLAN",
                "status": "done",
                "duration_s": round(time.time() - start, 1),
                "detail": f"{len(result.get('sub_queries', []))} 个子查询"
            }]
        }

    async def harvest_evidence(self, query: str, sub_queries: List[str],
                               doc_id: str = "all") -> List[Dict]:
        """ [V250.0] Step 2: Harvester Phase """
        start = time.time()
        from backend.app.services.intelligence.retrieval.graph.adapter import create_initial_court_state
        from backend.app.services.intelligence.retrieval.constants import RetrievalPhase

        state = create_initial_court_state(query, doc_id=doc_id)
        state["sub_queries"] = sub_queries

        harvest_func = self.court.nodes[RetrievalPhase.HARVEST]
        harvest_result = await harvest_func(state)
        pool = harvest_result.get("evidence_pool", [])

        return {
            "evidence_pool": pool,
            "phase_log": [{
                "step": "HARVEST",
                "status": "done",
                "duration_s": round(time.time() - start, 1),
                "detail": f"{len(pool)} 条证据"
            }]
        }

    async def audit_evidence(self, query: str, evidence_ids: List[str],
                              evidence_pool: Optional[List[Dict]] = None,
                              doc_id: str = "all") -> Dict[str, Any]:
        """ [V250.0] Step 3: Auditor Phase """
        start = time.time()
        from backend.app.services.intelligence.retrieval.graph.adapter import create_initial_court_state
        from backend.app.services.intelligence.retrieval.constants import RetrievalPhase

        state = create_initial_court_state(query, doc_id=doc_id)
        if evidence_pool:
            state["evidence_pool"] = evidence_pool
        else:
            state["evidence_pool"] = [{"id": eid, "claims": [], "origin": "TEMP"} for eid in evidence_ids]

        audit_func = self.court.nodes[RetrievalPhase.AUDIT]
        audit_result = await audit_func(state)
        pool = audit_result.get("evidence_pool", [])
        conflicts = audit_result.get("conflicts", [])

        return {
            "conflicts": conflicts,
            "claim_weights": audit_result.get("claim_weights", {}),
            "evidence_pool": pool,
            "phase_log": [{
                "step": "AUDIT",
                "status": "done",
                "duration_s": round(time.time() - start, 1),
                "detail": f"{len(conflicts)} 处冲突 | {len(pool)} 条活跃"
            }]
        }

    async def arbitrate_conflict(self, query: str, audited_data: Dict[str, Any],
                                  conflict_id: str, resolution: str,
                                  human_notes: str = "") -> Dict[str, Any]:
        """
        人工仲裁：接收人类对 RED 冲突的裁定，调整 claim_weights，执行 synthesize。
        resolution: "accept_a" | "accept_b" | "reject_both" | "merge"
        """
        conflicts = audited_data.get("conflicts", [])
        target = next((c for c in conflicts if conflict_id in c.get("description", "")), None)
        target = target or (conflicts[0] if conflicts else None)
        if not target:
            return {"error": f"Conflict '{conflict_id}' not found in audited_data"}

        packages = target.get("packages", [])
        weights = audited_data.get("claim_weights", {}).copy()

        # 按 source_name 分组（LLM 可能返回多个 chunk 分别对应各条款）
        groups: Dict[str, list] = {}
        for p in packages:
            src = p.get("source_name", "unknown")
            cid = p.get("chunk_id")
            if cid:
                groups.setdefault(src, []).append(cid)

        group_keys = list(groups.keys())
        group_a_ids = groups.get(group_keys[0], []) if len(group_keys) > 0 else []
        group_b_ids = groups.get(group_keys[1], []) if len(group_keys) > 1 else []

        # 仲裁权重：采纳方 0.95，驳回方 0.15，全驳 0.05，合并 0.50
        W_ACCEPT = 0.95
        W_REJECT = 0.15
        W_DISMISS_ALL = 0.05
        W_MERGE = 0.50

        if resolution == "accept_a":
            for cid in group_a_ids: weights[cid] = W_ACCEPT
            for cid in group_b_ids: weights[cid] = W_REJECT
        elif resolution == "accept_b":
            for cid in group_a_ids: weights[cid] = W_REJECT
            for cid in group_b_ids: weights[cid] = W_ACCEPT
        elif resolution == "reject_both":
            for cid in group_a_ids + group_b_ids: weights[cid] = W_DISMISS_ALL
        elif resolution == "merge":
            for cid in group_a_ids + group_b_ids: weights[cid] = W_MERGE

        remaining = [c for c in conflicts if c.get("description") != target.get("description")]
        audited_data["conflicts"] = remaining
        audited_data["claim_weights"] = weights
        audited_data["human_arbitration"] = {
            "conflict_description": target.get("description", ""),
            "resolution": resolution,
            "notes": human_notes,
        }
        return await self.synthesize_verdict(query, audited_data)

    async def synthesize_verdict(self, query: str, audited_data: Dict[str, Any],
                                  doc_id: str = "all") -> Dict[str, Any]:
        """ [V250.0] Step 4: Synthesizer Phase """
        start = time.time()
        from backend.app.services.intelligence.retrieval.graph.adapter import (
            create_initial_court_state,
            adapt_court_state_to_hybrid_output
        )
        from backend.app.services.intelligence.retrieval.constants import RetrievalPhase

        state = create_initial_court_state(query, doc_id=doc_id)
        state.update(audited_data)

        synth_func = self.court.nodes[RetrievalPhase.SYNTHESIZE]
        synth_result = await synth_func(state)
        state.update(synth_result)

        final_output = adapt_court_state_to_hybrid_output(state)

        verdict_data = synth_result.get("verdict", {})
        consensus = verdict_data.get("internal_consensus", []) if verdict_data else []

        evolution_proposal = []
        for chunk in state.get("evidence_pool", []):
            if chunk.get("origin") != "TEMP":
                evolution_proposal.append({
                    "chunk_id": chunk.get("id", ""),
                    "content": chunk.get("content", ""),
                    "logic_tags": chunk.get("claims", []),
                    "document_id": chunk.get("doc_id", ""),
                })

        return {
            "verdict": final_output.get("final_answer"),
            "confidence": final_output.get("confidence"),
            "cited_sources": final_output.get("cited_sources", []),
            "evolution_proposal": evolution_proposal,
            "phase_log": [{
                "step": "SYNTHESIZE",
                "status": "done",
                "duration_s": round(time.time() - start, 1),
                "detail": f"{len(consensus)} 条客观真理" if consensus else "已判决"
            }]
        }

    async def hybrid_ask(self, query: str, doc_id: str = "all",
                         chat_id: Optional[str] = None,
                         enable_online: bool = False,
                         sync_to_bitable: bool = False,
                         limit: int = 10,
                         api_key: Optional[str] = None) -> List[Dict]:
        """
        Retrieval QA: Runs LogicCourt full graph (PLAN→HARVEST→AUDIT→SYNTHESIZE→EVOLVE).
        """
        from backend.app.services.intelligence.retrieval.graph.adapter import (
            create_initial_court_state,
            adapt_court_state_to_hybrid_output,
        )
        # Phase 1: Run LogicCourt full graph via injected orchestrator
        initial_state = create_initial_court_state(query, doc_id=doc_id)
        court_state = await self.court.run_from_state(initial_state)

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
            "phase_log": result.get("phase_log", []),   #  [V230.0] 阶段时间线
        }]

        #  [V210.0] 证据溯源：将证据链追加到结果列表，供 CLI 渲染溯源表格
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

        #  [V102.1] Sovereign Evolution: Prepare a proposal instead of auto-ingesting.
        evolution_proposal = []
        evidence_pool = court_state.get("evidence_pool", [])
        for chunk in evidence_pool:
            evolution_proposal.append({
                "chunk_id": chunk.get("id", ""),
                "content": chunk.get("content", ""),
                "logic_tags": chunk.get("claims", chunk.get("logic_tags", [])),
                "document_id": chunk.get("doc_id", ""),
            })
        final_results[0]["evolution_proposal"] = evolution_proposal

        # 4. Reporting logic
        target_chat = chat_id or settings.FEISHU_DEFAULT_CHAT_ID
        if target_chat:
            await self.reporter.report_result(
                final_results[0], target_chat,
            )

        if sync_to_bitable:
            # Pass the proposal to the reporter for potential "Pending Review" status
            await self.reporter.sync_asset(final_results[0], {"proposal": evolution_proposal})

        return final_results

    def get_chunk_history(self, chunk_id: str, limit: int = 20) -> List[Dict]:
        return self.git_version_control.get_chunk_history(chunk_id, limit)

    def diff_chunks(self, chunk_id: str, old_commit: str,
                    new_commit: str) -> str:
        return self.git_version_control.diff_chunks(
            chunk_id, old_commit, new_commit,
        )
