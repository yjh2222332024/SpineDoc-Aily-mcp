"""
HarvesterNode - Concurrent Evidence Gathering Expert
===================================================
Responsibility:
1. Fetch missions (sub_queries) from the shared state.
2. Launch parallel harvesting: SovereignSentry (Local) + WitnessExpert (Online).
3. Normalize results into the Unified Evidence Schema.
4. Update the centralized evidence_pool.
"""

import asyncio
import logging
from typing import List, Dict, Any
from .schema import CourtState
from ..sovereign_sentry import SovereignSentry
from ..experts.witness_expert import WitnessExpert

logger = logging.getLogger(__name__)

class HarvesterNode:
    """
    🚀 [V185.0] 并行收割节点：利用 asyncio.gather 实现极速双路取证。
    """
    def __init__(self, memory=None):
        self.sentry = SovereignSentry()
        self.witness = WitnessExpert()
        self.memory = memory  # A-MEM 记忆接口

    async def harvest(self, state: CourtState) -> Dict[str, Any]:
        investigation_order = state.get("investigation_order")
        if investigation_order:
            return await self._harvest_subpoena(investigation_order, state)

        missions = state.get("sub_queries", [])
        if not missions:
            print("⚠️ [HarvesterNode] 无取证任务，跳过收割。")
            return {"next_step": "AUDIT"}

        print(f"📡 [HarvesterNode] 启动大规模并发收割：处理 {len(missions)} 个逻辑分面...")

        # 0. 先查询 A-MEM 记忆（如果有）
        memory_evidence = []
        if self.memory:
            try:
                for m in missions:
                    mem_results = await self.memory.query_memory(m, limit=3)
                    if mem_results:
                        for r in mem_results:
                            r["origin"] = "A-MEMORY"
                            r["is_sovereign"] = True
                        memory_evidence.extend(mem_results)
                if memory_evidence:
                    print(f"🧠 [HarvesterNode] 从 A-MEM 获取 {len(memory_evidence)} 条记忆证据")
            except Exception as e:
                logger.warning(f"⚠️ [HarvesterNode] A-MEM 查询失败: {e}")

        # 1. 扇出任务 (Fan-out)
        # 我们为每一个子问题同时开启：本地主权定位 + 云端联网质证
        tasks = []
        for m in missions:
            tasks.append(self._harvest_local(m))
            tasks.append(self._harvest_online(m))

        # 2. 并行出击 (Wait for all)
        # 注意：这里我们使用 gather，让用户的手机 IO 效率达到物理极限
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 3. 结果入账 (Normalization & Flattening)
        new_evidence = []
        for res in results:
            if isinstance(res, list):
                new_evidence.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"❌ [HarvesterNode] 取证任务发生物理崩溃: {res}")

        print(f"✅ [HarvesterNode] 收割入账完成：新增 {len(new_evidence)} 条多维证据。")

        # 4. 指向下个阶段并回填物理座标
        # 🚀 物理确权：从本地收割结果中提取确凿的星系 Record ID
        target_gids = []
        for e in new_evidence:
            if e.get("origin") == "LOCAL_GALAXY":
                # 兼容多种可能的 ID 存放位置
                g_ids = e.get("galaxy_ids") or e.get("target_galaxy_ids")
                if g_ids:
                    target_gids.extend(g_ids if isinstance(g_ids, list) else [g_ids])
        
        # 如果从证据里没捞到，直接去查 state 里的备份（如果 Sentry 有存的话）
        final_gids = list(set([gid for gid in target_gids if gid]))
        print(f"📍 [HarvesterNode] 物理定位完成，锁定目标星系: {final_gids}")

        return {
            "evidence_pool": new_evidence,
            "target_galaxy_ids": final_gids,
            "next_step": "AUDIT"
        } if not memory_evidence else {
            "evidence_pool": memory_evidence + new_evidence,
            "target_galaxy_ids": final_gids,
            "next_step": "AUDIT"
        }

    async def _harvest_local(self, sub_query: str) -> List[Dict]:
        """局部路径：主权哨兵定位 + 逻辑脱水"""
        try:
            # 1. 物理收割
            evidence = await self.sentry.route_query(sub_query, limit=3)
            
            # 2. 🚀 [V185.3] 逻辑脱水：对主权证据进行原子解构
            from backend.app.services.rag.llm_service import llm_service
            
            distillation_tasks = [self.witness._distill_evidence(e, llm_service) for e in evidence]
            refined_local = await asyncio.gather(*distillation_tasks)
            
            for e in refined_local:
                e["origin"] = "LOCAL_GALAXY"
                e["is_sovereign"] = True
            return refined_local
        except Exception as e:
            logger.warning(f"⚠️ [HarvesterNode] 本地收割受挫 ({sub_query[:20]}): {e}")
            return []

    async def _harvest_online(self, sub_query: str) -> List[Dict]:
        """局部路径：联网证人取证"""
        try:
            # WitnessExpert 内部已经集成了 Zhipu Web Search 与 原子主张提取
            pkg = await self.witness.retrieve([sub_query])
            evidence = pkg.get("evidence_chunks", [])
            for e in evidence:
                e["origin"] = "INTERNET_WITNESS"
                e["is_sovereign"] = False
            return evidence
        except Exception as e:
            logger.warning(f"⚠️ [HarvesterNode] 联网质证失败 ({sub_query[:20]}): {e}")
            return []

    async def _harvest_subpoena(self, order: str, state: CourtState) -> Dict[str, Any]:
        """执行补充侦查：根据 investigation_order 收集额外证据，追加到现有池。"""
        print(f"📜 [HarvesterNode] 执行补充侦查令: {order[:60]}...")

        local_task = self._harvest_local(order)
        online_task = self._harvest_online(order)
        results = await asyncio.gather(local_task, online_task, return_exceptions=True)

        new_evidence = []
        for res in results:
            if isinstance(res, list):
                new_evidence.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"❌ [HarvesterNode] 补充侦查失败: {res}")

        existing_pool = state.get("evidence_pool", [])
        merged_pool = existing_pool + new_evidence

        print(f"✅ [HarvesterNode] 补充侦查完成：新增 {len(new_evidence)} 条证据，池中共 {len(merged_pool)} 条。")

        return {
            "evidence_pool": merged_pool,
            "investigation_order": None,  # 清除传唤令
            "re_harvest_count": state.get("re_harvest_count", 0) + 1,
            "next_step": "AUDIT",
        }

harvester_node = HarvesterNode()
