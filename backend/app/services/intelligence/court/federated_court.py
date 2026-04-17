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
from backend.app.services.knowledge.graph_weaver import GraphWeaver
from uuid import uuid4

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
        self.graph_weaver = GraphWeaver(session)  # 🕸️ [V7.0] 逻辑织网缝合者
        self.evidence_packages = []  # 保存证据包供测试访问

    async def hear(
        self,
        query: str,
        limit_per_galaxy: int = 3,
        enable_online: bool = False
    ) -> Dict[str, Any]:
        """
        开庭审理：完整的联邦法庭流程
        """
        start_time = time.time()  # 🏛️ 物理纪律：记录开庭瞬间
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

        # --- 🕸️ [V7.0] 逻辑织网：缝合关系 ---
        print("\n🕸️ [阶段 4] 逻辑织网...")
        try:
            # 从裁决书中提取 proposed_relationships
            relationships = self._extract_relationships_from_verdict(verdict)
            if relationships:
                # 生成临时 verdict_id 用于审计追溯
                import uuid
                verdict_id = str(uuid.uuid4())
                verdict["id"] = verdict_id  # 附加到裁决书

                # 调用 GraphWeaver 缝合关系
                created = self.graph_weaver.weave_from_verdict(verdict)
                print(f"   ↳ 缝合 {len(created)} 条关系")
            else:
                print("   ↳ 无关系声明，跳过织网")
        except Exception as e:
            # 织网失败不阻塞法庭流程，仅记录日志
            print(f"   ⚠️ 织网失败：{e}")

        # --- 🖋️ [V51.0] 外交官整合答案：把法条变成人话 ---
        print("\n🖋️ [阶段 5] 外交官整合答案...")
        from .synthesizer import Synthesizer
        synthesizer = Synthesizer()

        final_answer = await synthesizer.weave_answer(
            query=query,
            verdict=verdict,
            evidence_packages=evidence_packages,
            temperature=0.7  # 🚀 0.7 的灵魂温度：用于创造性整合
        )

        # 用外交官的"人话"替换掉法官的"法条"
        verdict["final_answer"] = final_answer
        print("✅ 外交官完成答案整合")

        # --- ⚖️ [V8.0] 物理存档：记录司法判决书 ---
        try:
            from backend.app.core.models import CourtVerdict
            from uuid import UUID
            
            # 使用现有 verdict["id"] 或生成新的
            v_id = verdict.get("id")
            if not v_id:
                v_id = uuid4()
                verdict["id"] = str(v_id)
            elif isinstance(v_id, str):
                v_id = UUID(v_id)

            archive = CourtVerdict(
                id=v_id,
                query=query,
                final_answer=final_answer,
                reasoning_thought=verdict.get("reasoning", ""), 
                verdict_decision=verdict.get("decision", "ACCEPTED"),
                cited_galaxies=verdict.get("cited_galaxies", []),
                confidence_score=verdict.get("confidence", 0.0),
                duration_ms=int((time.time() - start_time) * 1000)
            )
            self.session.add(archive)
            await self.session.commit()
            print(f"📜 [Court] 判决书已存档至数据库 (ID: {str(v_id)[:8]})")
        except Exception as e:
            print(f"⚠️ [Court] 判决书存档失败：{e}")
            await self.session.rollback()

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

    def _extract_relationships_from_verdict(self, verdict: Dict) -> List[Dict]:
        """
        从裁决书中提取 proposed_relationships

        关系可能存在于：
        1. conflicts_resolved[].proposed_relationships
        2. knowledge_delta.proposed_relationships

        Args:
            verdict: 裁决书

        Returns:
            关系声明列表
        """
        relationships = []

        # 1. 从冲突裁决中提取
        conflicts = verdict.get("conflicts_resolved", [])
        for conflict in conflicts:
            proposed = conflict.get("proposed_relationships", [])
            relationships.extend(proposed)

        # 2. 从知识增量中提取（如果有）
        delta = verdict.get("knowledge_delta", {})
        if isinstance(delta, dict):
            proposed = delta.get("proposed_relationships", [])
            relationships.extend(proposed)

        return relationships
