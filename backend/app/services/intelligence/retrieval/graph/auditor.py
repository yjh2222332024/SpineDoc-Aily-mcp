"""
AuditorNode - Logic Consistency & Conflict Detection Expert
==========================================================
Responsibility:
1. Extract and align atomic claims from the shared pool.
2. Group claims by semantic intent to detect logical contradictions.
3. Manage evidence weights and archive stale/conflicting state.
"""

import logging
from typing import List, Dict, Any, Optional
from .schema import CourtState
from ..utils.conflict_detector import ConflictDetector

logger = logging.getLogger(__name__)

_detector = ConflictDetector()


async def _detect_conflicts_llm(pool: List[Dict], query: str) -> List[Dict]:
    """
    Detect conflicts using LLM-based ConflictDetector.
    Rebuilds source_results format from flat evidence_pool.
    """
    # Group evidence by source_name into source_results format
    source_map: Dict[str, Dict] = {}
    for e in pool:
        src_name = e.get("source_name", "Unknown")
        if src_name not in source_map:
            source_map[src_name] = {
                "source_name": src_name,
                "doc_id": e.get("doc_id", ""),
                "evidence_chunks": [],
            }
        source_map[src_name]["evidence_chunks"].append(e)

    source_results = list(source_map.values())
    if len(source_results) < 2:
        return []

    return await _detector.detect(source_results, query)


class AuditorNode:
    """
    🚀 [V185.0] 审计法院节点：负责识别逻辑冲突并执行状态降权。
    """
    async def audit(self, state: CourtState) -> Dict[str, Any]:
        pool = state.get("evidence_pool", [])
        if not pool:
            print("⚠️ [AuditorNode] 证据库为空，跳过审计。")
            return {"next_step": "SYNTHESIZE"}

        print(f"⚖️ [AuditorNode] 正在审计 {len(pool)} 条多维证据...")

        # 1. 冲突探测 (Conflict Detection via LLM)
        conflicts = await _detect_conflicts_llm(pool, state.get("query", ""))
        
        # 2. 初始化权重表
        weights = state.get("claim_weights", {})
        for e in pool:
            eid = e.get("id")
            if eid and eid not in weights:
                weights[eid] = 1.0

        # 3. 🚀 [V185.1] 逻辑辩论与裁定 (The Debate Protocol)
        subpoena_order = None
        if conflicts:
            print(f"🔴 [AuditorNode] 检测到 {len(conflicts)} 处逻辑裂痕，启动联邦辩论...")
            from backend.app.services.ingestion.llm_service import llm_service

            # 对每一个冲突点执行庭审
            for c in conflicts:
                new_weights = await self._debate_and_arbitrate(c, pool, llm_service)
                weights.update(new_weights)

            # 检查是否有不确定的冲突，需要补充侦查
            subpoena_order = self._check_uncertain_conflicts(conflicts, weights, state.get("re_harvest_count", 0))
        else:
            print("🟢 [AuditorNode] 未发现明显逻辑冲突。")

        # 4. 物理分层建议与状态裁剪 (The Diet)
        archive_candidates = []
        active_pool = []
        for e in pool:
            weight = weights.get(e["id"], 1.0)
            if weight < 0.2:
                print(f"❄️ [AuditorNode] 证据 {e['id']} 置信度过低 ({weight:.2f})，标记为 L3 归档。")
                archive_candidates.append(e)
            else:
                # 🚀 [V185.2] 逻辑脱水：裁剪正文内容，节省 Token
                pruned_e = {
                    "id": e["id"],
                    "claims": e.get("claims", []),
                    "origin": e.get("origin"),
                    "score": e.get("score", 0.0),
                    "confidence": e.get("confidence", 0.0),
                    "color": e.get("color"),
                    # 只有归档文件才保留原始全文，活跃池只留精华
                    "content": "[PRUNED]" 
                }
                active_pool.append(pruned_e)

        print(f"✂️ [AuditorNode] 状态裁剪完成：活跃池正文已物理脱水。")

        if subpoena_order:
            print(f"📜 [AuditorNode] 存在不确定冲突，签发补充侦查令: {subpoena_order[:60]}...")
            return {
                "conflicts": conflicts,
                "claim_weights": weights,
                "evidence_pool": active_pool,
                "L3_archive": archive_candidates,
                "investigation_order": subpoena_order,
                "next_step": "HARVEST",  # 发回补充侦查
            }

        return {
            "conflicts": conflicts,
            "claim_weights": weights,
            "evidence_pool": active_pool,
            "L3_archive": archive_candidates,
            "next_step": "SYNTHESIZE"
        }

    def _check_uncertain_conflicts(self, conflicts: List[Dict], weights: Dict, re_harvest_count: int) -> Optional[str]:
        """
        检查是否有无法确定胜负的冲突 — 双方权重接近（diff < 0.3）且都 > 0.2。
        如需要且未超过补充侦查上限，返回 investigation_order。
        """
        if re_harvest_count >= 1:
            return None  # 已经补充侦查过一次，不再重复

        for c in conflicts:
            packages = c.get("packages", [])
            if len(packages) < 2:
                continue
            ev_ids = [p["chunk_id"] for p in packages if "chunk_id" in p]
            if len(ev_ids) < 2:
                continue
            w_a = weights.get(ev_ids[0], 0.5)
            w_b = weights.get(ev_ids[1], 0.5)
            # 双方权重接近且都不低 — 无法明确裁决
            if abs(w_a - w_b) < 0.3 and w_a > 0.2 and w_b > 0.2:
                topic = c.get("description") or c.get("topic") or "unknown"
                return f"针对 '{topic}' 的争议需要更多证据以辅助裁决"

        return None

    async def _debate_and_arbitrate(self, conflict: Dict, pool: List[Dict], llm) -> Dict[str, float]:
        """
        模拟多代理辩论：让 LLM 扮演法官，对冲突方进行质证并给出降权系数。
        兼容新旧两种冲突格式：
          - 新格式: packages[*].chunk_id (from ConflictDetector)
          - 旧格式: evidence_a / evidence_b (legacy)
        """
        # 提取冲突涉及的证据 IDs（兼容两种格式）
        packages = conflict.get("packages", [])
        if packages:
            ev_ids = [p["chunk_id"] for p in packages if "chunk_id" in p]
            ev_a_id = ev_ids[0] if len(ev_ids) > 0 else None
            ev_b_id = ev_ids[1] if len(ev_ids) > 1 else None
            claims_a = [p.get("claim", "") for p in packages if p.get("chunk_id") == ev_a_id]
            claims_b = [p.get("claim", "") for p in packages if p.get("chunk_id") == ev_b_id]
            origin_a = packages[0].get("source_name", "Unknown")
            origin_b = packages[1].get("source_name", "Unknown") if len(packages) > 1 else "Unknown"
        else:
            ev_a_id = conflict.get("evidence_a")
            ev_b_id = conflict.get("evidence_b")
            ev_a = next((e for e in pool if e["id"] == ev_a_id), {})
            ev_b = next((e for e in pool if e["id"] == ev_b_id), {})
            claims_a = ev_a.get("claims", [])
            claims_b = ev_b.get("claims", [])
            origin_a = ev_a.get("origin", "Unknown")
            origin_b = ev_b.get("origin", "Unknown")

        prompt = f"""请作为联邦法院首席审计官，对以下逻辑冲突执行'闭门质证'。

【冲突主题】：{conflict.get('description', conflict.get('topic', 'Unknown'))}
【证据 A】(来源: {origin_a}): {claims_a}
【证据 B】(来源: {origin_b}): {claims_b}

审计准则：
1. 优先维护'LOCAL_GALAXY'（本地主权星系）的权威性，除非'INTERNET_WITNESS'（联网证人）提供了更高维度的物理事实。
2. 识别哪方可能存在幻觉、过时或误解。
3. 为双方给出最终的【置信度权重】(0.0 - 1.0)。

请严格输出 JSON 格式：{{"weights": {{"{ev_a_id}": 0.9, "{ev_b_id}": 0.1}}, "reasoning": "原因..."}}
"""
        try:
            res = await llm.chat_completion(prompt, response_format="json")
            return res.get("weights", {})
        except Exception as e:
            logger.error(f"❌ [AuditorNode] 质证失败: {e}")
            return {ev_a_id: 0.5, ev_b_id: 0.5} if ev_a_id and ev_b_id else {}

auditor_node = AuditorNode()
