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
from .schema import CourtState, GraphExecutionState
from ..local_retriever import LocalRetriever, SovereignSentry
from ..experts.online_retriever import OnlineRetriever, WitnessExpert

logger = logging.getLogger(__name__)

# 向后兼容别名
CourtState = GraphExecutionState

class EvidenceGatheringNode:
    """
    🚀 [V185.0] 证据收集节点：利用 asyncio.gather 实现极速双路取证。
    替代旧名称：HarvesterNode
    """
    def __init__(self, memory=None):
        self.sentry = SovereignSentry()
        self.witness = WitnessExpert()
        self.memory = memory  # A-MEM 记忆接口

    async def harvest(self, state: CourtState) -> Dict[str, Any]:
        investigation_order = state.get("investigation_order")
        if investigation_order:
            return await self._harvest_subpoena(investigation_order, state)

        # 🚀 [V220.0] 单文档快速路径：跳过 galaxy 路由，直插 documents→chunks
        doc_id = state.get("doc_id", "all")
        if doc_id and doc_id != "all":
            print(f"📄 [HarvesterNode] 单文档模式: {doc_id[:8]}...")
            return await self._harvest_single_doc(doc_id, state)

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
        # 🚀 [Dedupe] 先定位星系，再分发任务，避免重复请求
        # 合并所有 missions 的关键词，一次定位主星系
        combined_query = " ".join(missions)
        primary_galaxy_ids = await self._pre_locate_galaxies(combined_query)

        tasks = []
        for m in missions:
            tasks.append(self._harvest_local(m, pre_located_galaxies=primary_galaxy_ids))
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

        # 4. 🚀 [DocFilter] 如果指定了 doc_id，过滤掉非目标文档的证据
        target_doc_id = state.get("doc_id", "all")
        if target_doc_id and target_doc_id != "all":
            before = len(new_evidence)
            new_evidence = [
                e for e in new_evidence
                if str(e.get("doc_record_id", "")).startswith(target_doc_id)
                or str(e.get("doc_id", "")).startswith(target_doc_id)
            ]
            print(f"🔍 [HarvesterNode] doc_id 过滤: {before} → {len(new_evidence)} 条 (target: {target_doc_id})")

        # 5. 指向下个阶段并回填物理座标
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

    async def _harvest_single_doc(self, doc_id: str, state: CourtState) -> Dict[str, Any]:
        """🚀 [V220.0] 单文档直路：跳过 galaxy 路由，在目标文档分片内直接收割。"""
        missions = state.get("sub_queries", [])
        if not missions:
            print("⚠️ [HarvesterNode] 单文档模式无子查询，跳到 AUDIT。")
            return {"next_step": "AUDIT"}

        print(f"📄 [HarvesterNode] 单文档直路: {len(missions)} 个子查询")

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
            except Exception as e:
                logger.warning(f"⚠️ [HarvesterNode] A-MEM 查询失败: {e}")

        tasks = []
        for m in missions:
            tasks.append(self.sentry.route_query_by_document(doc_id, m, limit=5))
            tasks.append(self._harvest_online(m))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        new_evidence = []
        for res in results:
            if isinstance(res, list):
                new_evidence.extend(res)
            elif isinstance(res, Exception):
                logger.error(f"❌ [HarvesterNode] 单文档取证失败: {res}")

        target_gids = []
        for e in new_evidence:
            g_ids = e.get("galaxy_ids")
            if g_ids:
                target_gids.extend(g_ids if isinstance(g_ids, list) else [g_ids])

        final_gids = list(set(target_gids))
        print(f"✅ [HarvesterNode] 单文档收割完成: {len(new_evidence)} 条证据")

        return {
            "evidence_pool": (memory_evidence + new_evidence) if memory_evidence else new_evidence,
            "target_galaxy_ids": final_gids,
            "next_step": "AUDIT"
        }

    async def _pre_locate_galaxies(self, combined_query: str) -> List[str]:
        """🚀 [Dedupe] 预先定位主星系，避免每个 mission 重复请求"""
        try:
            # 只调用一次 Sentry 获取星系 ID
            territories = await self.sentry.pre_locate_galaxies(combined_query)
            return [t["source_id"] for t in territories if t.get("source_id")]
        except Exception as e:
            logger.warning(f"⚠️ [HarvesterNode] 星系预定位失败: {e}")
            return []

    async def _harvest_local(self, sub_query: str, pre_located_galaxies: List[str] = None) -> List[Dict]:
        """局部路径：主权哨兵定位 + 逻辑脱水（无 LLM，直接使用 Bitable AI 的 逻辑摘要）"""
        try:
            # 1. 物理收割（复用预定位星系，避免重复请求）
            evidence = await self.sentry.route_query(
                sub_query, limit=5, pre_located_galaxies=pre_located_galaxies
            )

            # 2. 🚀 [Opt] 跳过 LLM 蒸馏，直接使用 Bitable AI 已生成的逻辑摘要作为主张
            for e in evidence:
                summary = e.get("summary") or e.get("content", "")
                e["claims"] = [summary] if summary else []
                e["stability"] = 0.85  # 本地归档知识，默认稳定
                e["origin"] = "LOCAL_GALAXY"
                e["is_sovereign"] = True
                e["color"] = "GREEN"
                e["confidence"] = 0.85
            return evidence
        except Exception as e:
            import traceback
            logger.warning(f"⚠️ [HarvesterNode] 本地收割受挫 ({sub_query[:20]}): {e}")
            logger.warning(f"📍 [HarvesterNode] Traceback: {traceback.format_exc()[-500:]}")
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

harvester_node = EvidenceGatheringNode()

# 向后兼容实例别名
HarvesterNode = EvidenceGatheringNode
