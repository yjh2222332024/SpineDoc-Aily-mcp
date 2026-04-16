"""
🏛️ FederatedCourt - 联邦法庭统一入口
=======================================
职责：编排 Distributor、Collector、Moderator，完成多文档联邦检索。
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.config import settings
from .state import CourtState
from .distributor import Distributor
from .collector import Collector
from .moderator import Moderator


class FederatedCourt:
    """
    🏛️ 联邦法庭 (Federated Court)

    职责：
    编排完整的法庭流程：传唤 → 取证 → 裁决

    使用示例：
        court = FederatedCourt(session)
        verdict = await court.hear(query="RAG 如何优化检索？")
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.distributor = Distributor(session)
        self.collector = Collector()
        self.moderator = Moderator()
        self.evidence_packages = []  # 保存证据包供测试访问

    async def hear(
        self,
        query: str,
        limit_per_galaxy: int = 3,
        enable_online: bool = False
    ) -> Dict[str, Any]:
        """
        开庭审理：完整的联邦法庭流程

        Args:
            query: 用户查询
            limit_per_galaxy: 每个星系最多传唤的文档数
            enable_online: 是否激活联网证人

        Returns:
            verdict: 判决书 {
                "final_answer": str,
                "confidence": float,
                "cited_galaxies": List[str],
                "conflicts_resolved": List[Dict],
                "knowledge_delta": Dict,  # 知识增量
                "reasoning": str
            }
        """
        # 🚀 [V50.6] LLM 配置预检：发送探测请求验证 LLM 可用性
        llm_error = await self._probe_llm()
        if llm_error:
            print(f"❌ [FederatedCourt] LLM 不可用：{llm_error}")
            return {
                "final_answer": f"❌ LLM 服务不可用：{llm_error}",
                "confidence": 0.0,
                "cited_galaxies": [],
                "reasoning": "LLM 配置验证失败"
            }

        print("\n" + "=" * 60)
        print(f"🏛️ 联邦法庭开庭：{query[:settings.CONTEXT_COMMIT_QUERY_PREFIX]}...")
        if enable_online:
            print("🌐 [模式] 联网证人已激活，知识库可能更新")
        print("=" * 60)

        # --- 阶段 1: 传唤证人 ---
        print("\n📋 [阶段 1] 传唤证人...")
        state = CourtState()
        state["summoned_docs"] = await self.distributor.summon_witnesses(
            query,
            limit_per_galaxy=limit_per_galaxy
        )

        if not state["summoned_docs"]:
            print("⚠️ 未找到任何证人文档，使用备用策略...")
            # 兜底：返回一个空判决
            return {
                "final_answer": "未找到相关文档，无法生成判决。",
                "confidence": 0.0,
                "cited_galaxies": [],
                "reasoning": "Distributor 未找到任何相关文档"
            }

        # --- 阶段 2: 收集证据 ---
        print("\n📡 [阶段 2] 收集证据...")
        evidence_packages = await self.collector.collect_evidence(
            state["summoned_docs"],
            query,
            enable_online=enable_online  # ← 传递联网开关
        )
        state["evidence_packages"] = evidence_packages
        self.evidence_packages = evidence_packages  # 保存供测试访问

        # --- 阶段 3: 裁决冲突 ---
        print("\n👨‍⚖️ [阶段 3] 裁决冲突...")
        verdict = await self.moderator.adjudicate(evidence_packages, query)
        state["verdict"] = verdict

        # --- 休庭 ---
        state["is_court_adjourned"] = True
        print("\n" + "=" * 60)
        print("✅ 联邦法庭休庭")
        print("=" * 60)

        return verdict

    async def _probe_llm(self) -> Optional[str]:
        """🚀 [V50.6] 轻量级 LLM 可用性探测

        Returns:
            None 如果 LLM 可用，错误消息字符串如果不可用
        """
        from backend.app.core.config import settings
        from openai import AsyncOpenAI

        # 1. 检查配置是否存在
        if not settings.LLM_API_KEY:
            return "LLM_API_KEY 未配置，请在 .env 文件中设置"
        if not settings.LLM_BASE_URL:
            return "LLM_BASE_URL 未配置，请在 .env 文件中设置"

        # 2. 发送一个轻量级探测请求
        try:
            client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

            # 探测请求：只用一个简单的 prompt 测试连通性
            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=settings.LLM_MODEL_NAME,
                    messages=[{"role": "user", "content": "OK"}],
                    max_tokens=5
                ),
                timeout=10.0
            )
            if not response or not response.choices:
                return "LLM 探测请求返回空响应"
            return None
        except asyncio.TimeoutError:
            return "LLM 探测请求超时 (10s)，请检查 API_ENDPOINT 是否可达"
        except Exception as e:
            return f"LLM 探测请求失败：{e}"

    async def hear_single(self, query: str, doc_id: str) -> Dict[str, Any]:
        """
        单文档听证（用于测试或精确查询）
        """
        print(f"\n🏛️ 单文档听证：{query[:settings.CONTEXT_COMMIT_QUERY_PREFIX]}... @ {doc_id[:settings.CONTEXT_COMMIT_DOC_ID_PREFIX]}")

        # 直接调用 witness_graph
        from backend.app.services.intelligence.witness.graph import witness_graph

        initial_state = {
            "query": query,
            "doc_id": doc_id,
            "toc": [],
            "sub_queries": [],
            "fingerprint_pool": [],
            "selected_ids": [],
            "pro_evidence": [],
            "citation_ids": [],
            "is_sufficient": False,
            "final_answer": ""
        }

        result = await witness_graph.ainvoke(initial_state)
        return {
            "final_answer": result.get("final_answer", ""),
            "confidence": 1.0 if result.get("is_sufficient") else 0.5,
            "cited_galaxies": [],
            "reasoning": "单文档听证，无冲突检测"
        }
