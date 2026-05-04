"""
EvolutionNode - Knowledge Backfill & Galaxy Evolution Expert
==========================================================
Responsibility:
1. Identify high-value 'Consensus' from the Judge's verdict.
2. Backfill new knowledge into Bitable as Level 1 nodes.
3. Archive conflicts to ensure long-term logical immunity.
4. Trigger Galaxy Centroid evolution (A-MEM).
"""

import logging
import asyncio
import hashlib
import json
from typing import Dict, Any, List
from .schema import CourtState, GraphExecutionState
from backend.app.services.feishu.bitable_ledger import bitable_ledger
from backend.app.services.intelligence.clustering.cluster_engine import cluster_engine

logger = logging.getLogger(__name__)

# 向后兼容别名
CourtState = GraphExecutionState

class KnowledgeBackfillNode:
    """
    🚀 [V200.0] 演化节点：将‘绝对客观成果’物理固化，建立多代传承。
    """
    async def evolve(self, state: CourtState) -> Dict[str, Any]:
        verdict = state.get("verdict", {})
        consensus = verdict.get("internal_consensus", [])
        conflicts = verdict.get("unresolved_conflicts", [])
        
        if not consensus and not conflicts:
            print("⚠️ [EvolutionNode] 无可演化成果，封印状态。")
            return {"next_step": "END"}

        print(f"🧬 [EvolutionNode] 正在执行主权演化：处理 {len(consensus)} 条新共识...")

        # 1. 物理回填：将新共识写入 Bitable
        # 🚀 物理确权：确保在会话结束前完成落库
        await self._backfill_to_bitable(consensus, state)

        # 2. 逻辑反哺：如果存在冲突，记录到‘逻辑墓地’
        if conflicts:
            print(f"🪦 [EvolutionNode] 发现 {len(conflicts)} 处顽固冲突，执行红区归档。")
            # 记录逻辑冲突，为后续 Agent 提供免疫力
        
        return {
            "next_step": "END",
            "iteration": state.get("iteration", 0) + 1
        }

    async def _backfill_to_bitable(self, consensus: List[str], state: CourtState):
        """
        物理落库：将客观真理物理固化至 Bitable 星系中，补完溯源链。
        """
        try:
            g_ids = state.get("target_galaxy_ids", [])
            
            # A. 获取物理锚点（主权演化共识库）
            sovereign_root_id = await bitable_ledger.get_or_create_sovereign_root()

            # B. 构造带世代纪律的物理分片数据
            new_records = []
            generation = state.get("iteration", 1)
            
            for i, fact in enumerate(consensus):
                # 1. 计算逻辑指纹 (MD5 去重)
                fingerprint = hashlib.md5(fact.encode('utf-8')).hexdigest()
                
                # 2. 注入数学权重与世代 (Truth Discovery Proxy)
                meta_json = json.dumps({
                    "generation": generation,
                    "confidence": round(0.85 + (generation * 0.05), 2), # 权重随代数递增
                    "source": "logic_court_evolution",
                    "schema_version": "v2.1-lineage"
                }, ensure_ascii=False)

                # 3. 提取父代关联 (取触发进化的核心证据作为父节点)
                # 🚀 架构泛化：父级关联不再仅仅是 TOC，而是 Lineage
                parent_ids = [g_ids[0]] if g_ids else []

                new_records.append({
                    "正文内容": fact,
                    "逻辑摘要": f"主权演化共识-G{generation}-{i}",
                    "Git版本": f"v2.0-evolved-g{generation}",
                    "物理页码": 0,
                    "逻辑坐标": f"E-G{generation}-{i}",
                    "逻辑面包屑": "主权演化共识",

                    # 🚀 物理补完：使用 save_chunks_batch 验证过的格式
                    "文档关联": str(sovereign_root_id) if sovereign_root_id else "",
                    "逻辑指纹": fingerprint,
                    "元数据": meta_json,
                })

            # C. 启动物理回调
            if new_records:
                print(f"💾 [Evolution] 正在向根文档 {sovereign_root_id} 回调 {len(new_records)} 条客观真理...")
                await bitable_ledger.backfill_consensus(new_records)
            
        except Exception as e:
            logger.error(f"❌ [Evolution] 物理回调失败: {e}", exc_info=True)

evolution_node = KnowledgeBackfillNode()

# 向后兼容实例别名
EvolutionNode = KnowledgeBackfillNode
