"""
RetrievalGraphOrchestrator - The Multi-Agent Graph Engine
===================================================
Responsibility:
1. Orchestrate the flow between specialized nodes.
2. Manage the centralized execution state.
3. Drive the system from Query to Evolution.
"""

import asyncio
import logging
import time
from typing import Dict, Any
from .schema import GraphExecutionState
from .planner import planner_agent
from .harvester import harvester_node
from .auditor import auditor_node
from .synthesizer import synthesizer_node
from .evolution import evolution_node
from ..constants import RetrievalPhase

logger = logging.getLogger(__name__)


class RetrievalGraphOrchestrator:
    """
    🚀 [V205.0] 检索图编排器：主权检索系统的中央引擎。
    替代旧名称：LogicCourtCoordinator
    """
    def __init__(self, memory=None):
        self.nodes = {
            RetrievalPhase.PLAN: planner_agent.plan,
            RetrievalPhase.HARVEST: harvester_node.harvest,
            RetrievalPhase.AUDIT: auditor_node.audit,
            RetrievalPhase.SYNTHESIZE: synthesizer_node.synthesize,
            RetrievalPhase.EVOLVE: evolution_node.evolve
        }
        if memory:
            harvester_node.memory = memory

    async def run(self, query: str, memory=None) -> Dict[str, Any]:
        """驱动检索图执行全链路"""
        if memory:
            harvester_node.memory = memory

        state: GraphExecutionState = {
            "query": query,
            "sub_queries": [],
            "internal_prior": "",
            "evidence_pool": [],
            "L3_archive": [],
            "claim_weights": {},
            "agreed_claims": [],
            "conflicts": [],
            "next_step": RetrievalPhase.QUERY_DECOMPOSITION,
            "iteration": 0,
            "verdict": None,
            "final_answer": None,
            "investigation_order": None,
            "re_harvest_count": 0,
        }

        print(f"🏛️ [RetrievalGraph] 开始执行: {query[:30]}...")
        return await self._graph_loop(state)

    async def run_from_state(self, state: GraphExecutionState) -> GraphExecutionState:
        """从预填充状态继续执行"""
        print(f"🏛️ [RetrievalGraph] 从 {state.get('next_step', '?')} 阶段继续...")
        return await self._graph_loop(state)

    async def _graph_loop(self, state: GraphExecutionState, max_duration: int = 600) -> GraphExecutionState:
        start_time = time.time()
        state.setdefault("phase_log", [])

        while state["next_step"] != RetrievalPhase.FINALIZED and state["iteration"] < 10:
            if time.time() - start_time > max_duration:
                return self._force_finalize(state)

            current_step = state["next_step"]
            node_func = self.nodes.get(current_step)

            if not node_func:
                logger.error(f"❌ [RetrievalGraph] 未定义的节点步骤: {current_step}")
                break

            phase_start = time.time()

            if current_step == RetrievalPhase.KNOWLEDGE_BACKFILL:
                state["next_step"] = RetrievalPhase.FINALIZED
                state["iteration"] += 1
                state["phase_log"].append({
                    "step": RetrievalPhase.KNOWLEDGE_BACKFILL, 
                    "status": "pending_consent",
                    "duration_s": round(time.time() - phase_start, 1),
                    "detail": "等待审计官核准演化提案",
                })
                break

            update = await node_func(state)
            state.update(update)

            state["phase_log"].append({
                "step": current_step,
                "status": "done",
                "duration_s": round(time.time() - phase_start, 1),
                "detail": _extract_phase_detail(current_step, update),
            })

        return state

    @staticmethod
    def _force_finalize(state: GraphExecutionState) -> GraphExecutionState:
        """强制终结：超时或达到最大迭代时，返回当前状态作为最终结果。"""
        print(f"⚠️ [RetrievalGraph] 执行强制终结，当前迭代次数: {state.get('iteration', 0)}")

        state["next_step"] = RetrievalPhase.FINALIZED
        if not state.get("final_answer"):
            state["final_answer"] = "系统超时未能完成完整推理，请重试或简化查询。"

        return state


# 向后兼容别名
CourtState = GraphExecutionState
LogicCourtCoordinator = RetrievalGraphOrchestrator

retrieval_graph = RetrievalGraphOrchestrator()
# 向后兼容别名
logic_court = retrieval_graph


def _extract_phase_detail(step: str, update: Dict[str, Any]) -> str:
    """Extract a human-readable detail from a node's update for phase_log."""
    if step == RetrievalPhase.EVIDENCE_GATHERING or step == "HARVEST":
        pool = update.get("evidence_pool", [])
        return f"{len(pool)} 条证据"
    if step == RetrievalPhase.EVIDENCE_VALIDATION or step == "AUDIT":
        conflicts = update.get("conflicts", [])
        pool = update.get("evidence_pool", [])
        parts = []
        if conflicts:
            parts.append(f"{len(conflicts)} 处冲突")
        if update.get("investigation_order"):
            parts.append("已签发补充侦查")
        parts.append(f"{len(pool)} 条活跃")
        return " | ".join(parts) if parts else "通过"
    if step == RetrievalPhase.VERDICT_SYNTHESIS or step == "SYNTHESIZE":
        verdict = update.get("verdict", {})
        consensus = verdict.get("internal_consensus", []) if verdict else []
        return f"{len(consensus)} 条客观真理" if consensus else "已判决"
    if step == RetrievalPhase.QUERY_DECOMPOSITION or step == "PLAN":
        missions = update.get("sub_queries", [])
        return f"{len(missions)} 个子查询"
    return ""
