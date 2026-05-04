"""
FederatedLogicCourt - Multi-Agent Consensus & Truth Arbitration
==============================================================
Responsibility:
1. Orchestrate specialized agents (Witness, Forensic, Diplomat).
2. Execute parallel evidence gathering.
3. Perform truth arbitration and confidence fusion.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from .sovereign_sentry import SovereignSentry
from .experts.witness_expert import WitnessExpert

logger = logging.getLogger(__name__)

class FederatedLogicCourt:
    """
    🚀 [V160.0] 联邦逻辑法院：SpineDoc 检索系统的最高权力机构。
    职责：解耦编排本地主权证据与外部证人证言。
    """
    def __init__(self):
        self.sentry = SovereignSentry()
        self.witness = WitnessExpert()
        self.threshold_for_witness = 0.7 # 唤醒证人的主权分红线

    async def arbitrate(self, query: str) -> Dict[str, Any]:
        """
        执行联邦裁定
        """
        print(f"🏛️ [FederatedCourt] 法院开庭，受理质询: {query[:30]}...")

        # 1. 启动主权哨兵：收割本地证据
        local_evidence = await self.sentry.route_query(query, limit=5)
        
        top_local_score = local_evidence[0].get("score", 0.0) if local_evidence else 0.0
        
        # 2. 动态裁定是否召唤“联网证人”
        # 如果本地主权分数不足，或者属于开放性问题，唤醒证人
        witness_package = None
        if top_local_score < self.threshold_for_witness:
            print(f"⚖️ [FederatedCourt] 本地主权置信度不足 ({top_local_score:.2f})，召唤联网证人...")
            witness_package = await self.witness.retrieve([query])
        
        # 3. 证据会师与平权融合
        final_package = self._fuse_evidence(local_evidence, witness_package)
        
        return final_package

    def _fuse_evidence(self, local_ev: List[Dict], witness_pkg: Optional[Dict]) -> Dict[str, Any]:
        """
        证据融合：将本地主权证据与外部证言进行物理合并
        """
        evidence_list = []
        
        # 注入本地证据
        for e in local_ev:
            e["is_sovereign"] = True
            e["origin"] = "LOCAL_GALAXY"
            evidence_list.append(e)
            
        # 注入外部证据
        if witness_pkg and "evidence_chunks" in witness_pkg:
            for e in witness_pkg["evidence_chunks"]:
                e["is_sovereign"] = False
                e["origin"] = "INTERNET_WITNESS"
                evidence_list.append(e)

        return {
            "evidence": evidence_list,
            "has_witness": witness_pkg is not None,
            "metadata": {
                "local_count": len(local_ev),
                "witness_count": len(witness_pkg["evidence_chunks"]) if witness_pkg else 0
            }
        }

federated_court = FederatedLogicCourt()
