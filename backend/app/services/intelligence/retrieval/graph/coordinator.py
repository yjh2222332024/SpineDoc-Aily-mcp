"""
LogicCourtCoordinator - The Multi-Agent Graph Engine
===================================================
Responsibility:
1. Orchestrate the flow between specialized nodes.
2. Manage the centralized CourtState.
3. Drive the system from Query to Evolution.
"""

import logging
import time
from typing import Dict, Any
from .schema import CourtState
from .planner import planner_agent
from .harvester import harvester_node
from .auditor import auditor_node
from .synthesizer import synthesizer_node
from .evolution import evolution_node

logger = logging.getLogger(__name__)

class LogicCourtCoordinator:
    """
    🚀 [V205.0] 联邦法院协调器：主权检索系统的中央引擎。
    """
    def __init__(self, memory=None):
        self.nodes = {
            "PLAN": planner_agent.plan,
            "HARVEST": harvester_node.harvest,
            "AUDIT": auditor_node.audit,
            "SYNTHESIZE": synthesizer_node.synthesize,
            "EVOLVE": evolution_node.evolve
        }
        # 将 memory 注入到 harvester_node
        if memory:
            harvester_node.memory = memory

    async def run(self, query: str, memory=None) -> Dict[str, Any]:
        """
        驱动逻辑法院执行全链路质证
        """
        if memory:
            harvester_node.memory = memory

        state: CourtState = {
            "query": query,
            "sub_queries": [],
            "internal_prior": "",
            "evidence_pool": [],
            "L3_archive": [],
            "claim_weights": {},
            "agreed_claims": [],
            "conflicts": [],
            "next_step": "PLAN",
            "iteration": 0,
            "verdict": None,
            "final_answer": None,
            "investigation_order": None,
            "re_harvest_count": 0,
        }

        print(f"🏛️ [LogicCourt] 开始受理案件: {query[:30]}...")
        return await self._graph_loop(state)

    async def run_from_state(self, state: CourtState) -> CourtState:
        """
        Run the graph loop from a pre-populated state.
        Skips PLAN/HARVEST if state.next_step is already past them.
        """
        print(f"🏛️ [LogicCourt] 从 {state.get('next_step', '?')} 阶段继续庭审...")
        return await self._graph_loop(state)

    async def _graph_loop(self, state: CourtState, max_duration: int = 180) -> CourtState:
        """
        Shared graph loop: executes nodes in sequence until END or max iterations.
        Each node returns the FULL replacement for its output fields (not incremental).
        Includes 3-minute timeout protection to prevent infinite loops.
        """
        start_time = time.time()

        while state["next_step"] != "END" and state["iteration"] < 10:
            # 超时保护
            if time.time() - start_time > max_duration:
                print("⏰ [LogicCourt] 超时 (3min)，强制终止迭代")
                return self._force_finalize(state)

            current_step = state["next_step"]
            node_func = self.nodes.get(current_step)

            if not node_func:
                logger.error(f"❌ [LogicCourt] 未定义的节点步骤: {current_step}")
                break

            update = await node_func(state)
            state.update(update)

        print(f"🏁 [LogicCourt] 庭审结束，输出最终裁定。")
        return state

    def _force_finalize(self, state: CourtState) -> CourtState:
        """
        强制终结：超时或达到最大迭代时，返回当前状态作为最终结果。
        """
        print(f"⚠️ [LogicCourt] 执行强制终结，当前迭代次数: {state.get('iteration', 0)}")

        state["next_step"] = "END"
        if not state.get("final_answer"):
            state["final_answer"] = "系统超时未能完成完整推理，请重试或简化查询。"

        return state

logic_court = LogicCourtCoordinator()
