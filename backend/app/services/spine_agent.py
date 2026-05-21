"""
SpineAgent - Single Agent with Concurrent Subagent HARVEST
===========================================================
Replaces the multi-agent RetrievalGraphOrchestrator with a single agent
that holds continuous state and uses concurrent subagents only for
the evidence gathering (HARVEST) phase.
"""
import asyncio
import time
import logging
from typing import Dict, Any, List, Optional

from backend.app.core.interfaces import IAgenticMemory, NullMemory
from backend.app.services.intelligence.retrieval.graph.schema import GraphExecutionState
from backend.app.services.intelligence.retrieval.graph.planner import planner_agent
from backend.app.services.intelligence.retrieval.graph.auditor import auditor_node
from backend.app.services.intelligence.retrieval.graph.synthesizer import synthesizer_node
from backend.app.services.intelligence.retrieval.graph.evolution import evolution_node
from backend.app.services.intelligence.retrieval.graph.harvest_subagents import (
    harvest_memory_subagent,
    harvest_local_subagent,
    harvest_online_subagent,
    HarvestSubagentResult,
)
from backend.app.services.intelligence.retrieval.graph.adapter import (
    adapt_court_state_to_hybrid_output,
)
from backend.app.services.intelligence.retrieval.local_retriever import LocalRetriever
from backend.app.services.intelligence.retrieval.experts.online_retriever import OnlineRetriever
from backend.app.services.intelligence.retrieval.utils.deduplicator import SemanticDeduplicator
from backend.app.services.intelligence.retrieval.constants import RetrievalPhase

logger = logging.getLogger(__name__)


class SpineAgent:
    """
    Single agent with continuous state for the LogicCourt pipeline.
    HARVEST phase uses concurrent subagents (A-MEM / Local / Online).
    """

    def __init__(
        self,
        memory: Optional[IAgenticMemory] = None,
        reporter=None,
        store=None,
    ):
        from backend.app.services.ingestion.embedding import embedding_service

        self.memory = memory or NullMemory()
        self.reporter = reporter
        self.store = store

        # Subagents (created once, reused across runs)
        self._sentry = LocalRetriever()
        self._witness = OnlineRetriever()
        self._deduplicator = SemanticDeduplicator(embedding_service=embedding_service)

        # Node objects (reused)
        self._planner = planner_agent
        self._auditor = auditor_node
        self._synthesizer = synthesizer_node
        self._evolution = evolution_node

        # Continuous state
        self._state: GraphExecutionState = self._initial_state()

        # Phase function map (built once)
        self._phase_funcs = {
            RetrievalPhase.PLAN: self.plan,
            RetrievalPhase.HARVEST: self.harvest,
            RetrievalPhase.AUDIT: self.audit,
            RetrievalPhase.SYNTHESIZE: self.synthesize,
            RetrievalPhase.EVOLVE: self.evolve,
        }

    @staticmethod
    def _initial_state() -> GraphExecutionState:
        return {
            "query": "",
            "doc_id": "all",
            "sub_queries": [],
            "evidence_pool": [],
            "L3_archive": [],
            "claim_weights": {},
            "agreed_claims": [],
            "conflicts": [],
            "verdict": None,
            "target_galaxy_ids": [],
            "investigation_order": None,
            "re_harvest_count": 0,
            "next_step": RetrievalPhase.PLAN,
            "iteration": 0,
            "final_answer": None,
            "phase_log": [],
        }

    def _apply_update(self, update: Dict[str, Any]):
        """
        Merge node update into self._state with domain-specific semantics.
        - evidence_pool: replace (auditor returns pruned version)
        - L3_archive: append + dedup (archive accumulates)
        - phase_log: append
        - all other keys: overwrite
        """
        for key, value in update.items():
            if key == "evidence_pool":
                self._state[key] = value
            elif key == "L3_archive" and key in self._state and isinstance(value, list):
                existing_ids = {e.get("id") for e in self._state[key] if e.get("id")}
                for item in value:
                    if item.get("id") not in existing_ids:
                        self._state[key].append(item)
            elif key == "phase_log" and isinstance(value, list):
                self._state.setdefault("phase_log", []).extend(value)
            else:
                self._state[key] = value

    def reset(self, query: str, doc_id: str = "all"):
        """Reset state for a new query."""
        self._state = self._initial_state()
        self._state["query"] = query
        self._state["doc_id"] = doc_id
        is_single_doc = bool(doc_id and doc_id != "all")
        if is_single_doc:
            self._state["sub_queries"] = [query]
            self._state["next_step"] = RetrievalPhase.HARVEST

    # ── Phase Methods ──────────────────────────────────────────

    async def plan(self) -> Dict[str, Any]:
        """PLAN phase: decompose query into sub-queries."""
        start = time.time()
        update = await self._planner.plan(self._state)
        self._apply_update(update)
        detail = f"{len(self._state.get('sub_queries', []))} 个子查询"
        self._state["phase_log"].append({
            "step": RetrievalPhase.PLAN, "status": "done",
            "duration_s": round(time.time() - start, 1), "detail": detail,
        })
        self._state["next_step"] = RetrievalPhase.HARVEST
        return update

    async def harvest(self) -> Dict[str, Any]:
        """
        HARVEST phase: concurrent subagent evidence gathering.
        Runs A-MEM, Local, and Online retrieval in parallel.
        """
        start = time.time()
        missions = self._state.get("sub_queries", [])
        doc_id = self._state.get("doc_id", "all")

        # Run 3 subagents concurrently
        mem_task = harvest_memory_subagent(self.memory, missions)
        local_task = harvest_local_subagent(self._sentry, missions, doc_id=doc_id)
        online_task = harvest_online_subagent(self._witness, missions)

        mem_result, local_result, online_result = await asyncio.gather(
            mem_task, local_task, online_task, return_exceptions=True,
        )

        # Merge results
        merged_pool = []
        for result in [mem_result, local_result, online_result]:
            if isinstance(result, Exception):
                logger.warning(f" [SpineAgent] subagent exception: {result}")
                continue
            if isinstance(result, HarvestSubagentResult):
                merged_pool.extend(result.evidence)

        # Semantic dedup
        deduped = await self._deduplicator.deduplicate(merged_pool)

        update = {"evidence_pool": deduped}
        self._apply_update(update)

        detail = f"{len(deduped)} 条证据 (deduped from {len(merged_pool)})"
        self._state["phase_log"].append({
            "step": RetrievalPhase.HARVEST, "status": "done",
            "duration_s": round(time.time() - start, 1), "detail": detail,
        })
        self._state["next_step"] = RetrievalPhase.AUDIT
        return update

    async def audit(self) -> Dict[str, Any]:
        """AUDIT phase: Bayesian weight aggregation + conflict detection."""
        start = time.time()
        update = await self._auditor.audit(self._state)
        self._apply_update(update)

        conflicts = self._state.get("conflicts", [])
        pool = self._state.get("evidence_pool", [])
        parts = []
        if conflicts:
            parts.append(f"{len(conflicts)} 处冲突")
        if self._state.get("investigation_order"):
            parts.append("已签发补充侦查")
        parts.append(f"{len(pool)} 条活跃")
        detail = " | ".join(parts) if parts else "通过"

        self._state["phase_log"].append({
            "step": RetrievalPhase.AUDIT, "status": "done",
            "duration_s": round(time.time() - start, 1), "detail": detail,
        })
        self._state["next_step"] = RetrievalPhase.SYNTHESIZE
        return update

    async def synthesize(self) -> Dict[str, Any]:
        """SYNTHESIZE phase: generate verdict from audited evidence."""
        start = time.time()
        update = await self._synthesizer.synthesize(self._state)
        self._apply_update(update)

        verdict = self._state.get("verdict") or {}
        consensus = verdict.get("internal_consensus", [])
        detail = f"{len(consensus)} 条客观真理" if consensus else "已判决"

        self._state["phase_log"].append({
            "step": RetrievalPhase.SYNTHESIZE, "status": "done",
            "duration_s": round(time.time() - start, 1), "detail": detail,
        })
        self._state["next_step"] = RetrievalPhase.EVOLVE
        return update

    async def evolve(self) -> Dict[str, Any]:
        """EVOLVE phase: knowledge backfill proposal (requires consent)."""
        self._state["phase_log"].append({
            "step": RetrievalPhase.EVOLVE, "status": "pending_consent",
            "duration_s": 0, "detail": "等待审计官核准演化提案",
        })
        self._state["next_step"] = RetrievalPhase.FINALIZED
        return {}

    async def run_full(self, query: str, doc_id: str = "all") -> Dict[str, Any]:
        """Run the full LogicCourt pipeline: PLAN→HARVEST→AUDIT→SYNTHESIZE→EVOLVE."""
        self.reset(query, doc_id)

        while self._state["next_step"] != RetrievalPhase.FINALIZED:
            step = self._state["next_step"]
            func = self._phase_funcs.get(step)
            if not func:
                logger.error(f" [SpineAgent] Unknown step: {step}")
                break
            await func()

        return self._export_result()

    def _export_result(self) -> Dict[str, Any]:
        """Export final result in the format expected by callers."""
        return adapt_court_state_to_hybrid_output(self._state)

    # ── State Accessors ────────────────────────────────────────

    @property
    def state(self) -> GraphExecutionState:
        return self._state

    def get_evidence_pool(self) -> List[Dict]:
        return self._state.get("evidence_pool", [])

    def get_claim_weights(self) -> Dict[str, float]:
        return self._state.get("claim_weights", {})

    def get_conflicts(self) -> List[Dict]:
        return self._state.get("conflicts", [])

    def get_phase_log(self) -> List[Dict]:
        return self._state.get("phase_log", [])
