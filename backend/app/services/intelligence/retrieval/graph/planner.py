"""
PlannerAgent - Strategic Decomposition Expert
============================================
Responsibility:
1. Analyze user query intent.
2. Decompose into atomic, searchable sub-queries.
3. Establish the initial reasoning direction for the Logic Court.
"""

import logging
from typing import Dict, Any
from backend.app.services.ingestion.llm_service import llm_service
from .schema import CourtState, GraphExecutionState

# 向后兼容别名（定义在类之后）
CourtState = GraphExecutionState

logger = logging.getLogger(__name__)

class QueryDecompositionAgent:
    """
     [V180.0] 战略规划代理：负责将主权挑战拆解为原子取证任务。
    """
    def __init__(self, llm_service=None):
        from backend.app.services.ingestion.llm_service import llm_service as default_llm
        self.llm_service = llm_service or default_llm

    async def plan(self, state: CourtState) -> Dict[str, Any]:
        query = state["query"]
        print(f" [PlannerAgent] 正在拆解战略意图: {query}")

        prompt = f"""请作为联邦法院首席法官，对以下用户的原始质询执行‘逻辑拆解’。
你的目标是将其拆解为 2-3 个独立的、可执行的子问题，以便‘主权哨兵’和‘证人专家’执行精准取证。

要求：
1. 每个子问题必须聚焦于一个具体的逻辑点（如物理步骤、理论依据、时效信息等）。
2. 保持子问题的原子性，避免模糊宽泛。
3. 严格输出 JSON 格式：{{"sub_queries": ["子问题1", "子问题2"]}}

【用户质询】：
{query}
"""
        try:
            # 质询云端 LLM 执行拆解
            res = await self.llm_service.chat_completion(prompt, response_format="json")
            sub_queries = res.get("sub_queries", [query])
            
            print(f" [PlannerAgent] 拆解完成，生成 {len(sub_queries)} 个取证任务。")
            
            # 返回状态更新
            return {
                "sub_queries": sub_queries,
                "next_step": "HARVEST",
                "iteration": state.get("iteration", 0) + 1
            }
        except Exception as e:
            logger.error(f" [PlannerAgent] 拆解失败: {e}")
            return {
                "sub_queries": [query], # 退化回原始查询
                "next_step": "HARVEST"
            }

planner_agent = QueryDecompositionAgent()
