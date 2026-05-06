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
from uuid import uuid4
from typing import List, Dict, Any
from .schema import CourtState, GraphExecutionState
from ..local_retriever import LocalRetriever, SovereignSentry
from ..experts.online_retriever import OnlineRetriever, WitnessExpert

logger = logging.getLogger(__name__)

from .schema import CourtState, GraphExecutionState, EvidenceSchema

class EvidenceGatheringNode:
    """
     [V185.0] 证据收集节点：利用 asyncio.gather 实现极速双路取证。
    """
    def __init__(self, sentry=None, witness=None, memory=None):
        self.sentry = sentry or SovereignSentry()
        self.witness = witness or WitnessExpert()
        self.memory = memory

    async def harvest(self, state: CourtState) -> Dict[str, Any]:
        """
        [V280.0] 统一收割入口：支持常规收割与补充侦查。
        """
        # 1. 检查是否有补充侦查令 (Subpoena)
        order = state.get("investigation_order")
        if order:
            return await self._harvest_subpoena(order, state)

        missions = state.get("sub_queries", [])
        target_doc_id = state.get("doc_id", "all")

        # 单文档模式走快路径：跳过星系路由，直接按文档关联字段过滤
        if target_doc_id != "all":
            return await self._harvest_single_doc(target_doc_id, state)

        # 1. 记忆收割 (A-MEM) — 并发查询
        memory_evidence = []
        if self.memory and missions:
            try:
                mem_coros = [self.memory.query_memory(m, limit=3) for m in missions]
                mem_results_list = await asyncio.gather(*mem_coros, return_exceptions=True)
                for mem_results in mem_results_list:
                    if isinstance(mem_results, Exception):
                        logger.warning(f" [Harvester] 记忆查询异常: {mem_results}")
                        continue
                    for r in mem_results:
                        # 强制规范化并验证
                        normalized = {
                            "id": r.get("id", str(uuid4())),
                            "content": r.get("content", ""),
                            "claims": r.get("logic_tags") or r.get("claims", []),
                            "origin": "A-MEMORY",
                            "confidence": r.get("confidence", 0.75),
                            "color": "BLUE",
                            "stability": 0.9,
                            "doc_id": r.get("document_id")
                        }
                        try:
                            valid_e = EvidenceSchema(**normalized)
                            memory_evidence.append(valid_e.dict())
                        except Exception as ve:
                            logger.warning(f" [Harvester] 记忆片段校验失败: {ve}")
            except Exception as e:
                logger.error(f" [Harvester] A-MEM 收割故障: {e}")

        # 2. 扇出收割 (Local + Online)
        tasks = []
        for m in missions:
            tasks.append(self._harvest_local(m))
            tasks.append(self._harvest_online(m))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        raw_new_evidence = []
        for res in results:
            if isinstance(res, list): raw_new_evidence.extend(res)

        # 3. 全量规范化与过滤
        final_pool = []
        seen_ids = set()
        all_candidate_evidence = memory_evidence + raw_new_evidence
        
        for e in all_candidate_evidence:
            try:
                # 统一校验
                valid_e = EvidenceSchema(**e)
                
                # 内部去重
                if valid_e.id in seen_ids:
                    continue
                seen_ids.add(valid_e.id)

                final_pool.append(valid_e.dict())
            except Exception as ve:
                logger.warning(f" [Harvester] 证据片校验失败: {ve}")

        print(f" [HarvesterNode] 收割入账完成：有效证据 {len(final_pool)} 条。")

        return {
            "evidence_pool": final_pool,
            "next_step": "AUDIT"
        }

    async def _harvest_single_doc(self, doc_id: str, state: CourtState) -> Dict[str, Any]:
        """ [V220.0] 单文档直路：跳过 galaxy 路由，在目标文档分片内直接收割。"""
        missions = state.get("sub_queries", [])
        if not missions:
            print(" [HarvesterNode] 单文档模式无子查询，跳到 AUDIT。")
            return {"next_step": "AUDIT"}

        print(f" [HarvesterNode] 单文档直路: {len(missions)} 个子查询")

        memory_evidence = []
        if self.memory and missions:
            try:
                mem_coros = [self.memory.query_memory(m, limit=3) for m in missions]
                mem_results_list = await asyncio.gather(*mem_coros, return_exceptions=True)
                for mem_results in mem_results_list:
                    if isinstance(mem_results, Exception):
                        logger.warning(f" [HarvesterNode] 记忆查询异常: {mem_results}")
                        continue
                    for r in (mem_results or []):
                        normalized = {
                            "id": r.get("id", str(uuid4())),
                            "content": r.get("content", ""),
                            "claims": r.get("logic_tags") or r.get("claims", []),
                            "origin": "A-MEMORY",
                            "confidence": r.get("confidence", 0.75),
                            "color": "BLUE",
                            "stability": 0.9,
                            "doc_id": r.get("document_id"),
                            "is_sovereign": True,
                        }
                        try:
                            valid_e = EvidenceSchema(**normalized)
                            memory_evidence.append(valid_e.dict())
                        except Exception as ve:
                            logger.warning(f" [HarvesterNode] 记忆片段校验失败: {ve}")
            except Exception as e:
                logger.warning(f" [HarvesterNode] A-MEM 查询失败: {e}")

        tasks = []
        for m in missions:
            tasks.append(self.sentry.route_query_by_document(doc_id, m, limit=5))
            tasks.append(self._harvest_online(m))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        new_evidence = []
        for res in results:
            if isinstance(res, list):
                for e in res:
                    try:
                        valid_e = EvidenceSchema(**e)
                        new_evidence.append(valid_e.dict())
                    except Exception as ve:
                        logger.warning(f" [HarvesterNode] 证据校验失败: {ve}")
            elif isinstance(res, Exception):
                logger.error(f" [HarvesterNode] 单文档取证失败: {res}")

        # 合并记忆证据 + 收割证据，去重
        seen_ids = set()
        final_pool = []
        for e in memory_evidence + new_evidence:
            eid = e.get("id")
            if eid and eid in seen_ids:
                continue
            if eid:
                seen_ids.add(eid)
            final_pool.append(e)

        target_gids = []
        for e in new_evidence:
            g_ids = e.get("galaxy_ids")
            if g_ids:
                target_gids.extend(g_ids if isinstance(g_ids, list) else [g_ids])

        final_gids = list(set(target_gids))
        print(f" [HarvesterNode] 单文档收割完成: {len(new_evidence)} 条证据")

        return {
            "evidence_pool": final_pool,
            "target_galaxy_ids": final_gids,
            "next_step": "AUDIT"
        }

    async def _pre_locate_galaxies(self, combined_query: str) -> List[str]:
        """ [Dedupe] 预先定位主星系，避免每个 mission 重复请求"""
        try:
            # 只调用一次 Sentry 获取星系 ID
            territories = await self.sentry.pre_locate_galaxies(combined_query)
            return [t["source_id"] for t in territories if t.get("source_id")]
        except Exception as e:
            logger.warning(f" [HarvesterNode] 星系预定位失败: {e}")
            return []

    async def _harvest_local(self, sub_query: str, pre_located_galaxies: List[str] = None) -> List[Dict]:
        """局部路径：主权哨兵定位 + 逻辑脱水（无 LLM，直接使用 Bitable AI 的 逻辑摘要）"""
        try:
            # 1. 物理收割（复用预定位星系，避免重复请求）
            evidence = await self.sentry.route_query(
                sub_query, limit=5, pre_located_galaxies=pre_located_galaxies
            )

            # 2.  [Opt] 跳过 LLM 蒸馏，直接使用 Bitable AI 已生成的逻辑摘要作为主张
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
            logger.warning(f" [HarvesterNode] 本地收割受挫 ({sub_query[:20]}): {e}")
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
            logger.warning(f" [HarvesterNode] 联网质证失败 ({sub_query[:20]}): {e}")
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
                logger.error(f" [HarvesterNode] 补充侦查失败: {res}")

        existing_pool = state.get("evidence_pool", [])
        merged_pool = existing_pool + new_evidence

        print(f" [HarvesterNode] 补充侦查完成：新增 {len(new_evidence)} 条证据，池中共 {len(merged_pool)} 条。")

        return {
            "evidence_pool": merged_pool,
            "investigation_order": None,  # 清除传唤令
            "re_harvest_count": state.get("re_harvest_count", 0) + 1,
            "next_step": "AUDIT",
        }

harvester_node = EvidenceGatheringNode()
