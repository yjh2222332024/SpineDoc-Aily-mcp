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
from .schema import CourtState, GraphExecutionState
from ..constants import (
    ARCHIVE_WEIGHT_THRESHOLD,
    UNCERTAINTY_WEIGHT_DIFF,
    MIN_WEIGHT_THRESHOLD,
    DEFAULT_WEIGHT,
    MAX_SUPPLEMENTARY_SEARCHES,
)

logger = logging.getLogger(__name__)

# 向后兼容别名
CourtState = GraphExecutionState


import math

class BayesianAggregator:
    """
     [V260.0] LogicCourt 贝叶斯融合器
    基于 AccuVote (Bayesian Truth Discovery) 算法。
    职责：计算多个冲突主张的后验概率。
    """
    SOURCE_PRIORS = {
        "LOCAL_GALAXY": 0.95,
        "A-MEMORY": 0.75,
        "INTERNET_WITNESS": 0.45,
        "UNKNOWN": 0.5
    }

    @classmethod
    def calculate_claim_confidence(cls, evidence_list: List[Dict]) -> float:
        """
        计算主张的集合置信度。
        公式：C = 1 - product(1 - W_s)
        体现：独立来源越多，置信度越高。
        """
        uncertainty = 1.0
        for e in evidence_list:
            origin = e.get("origin", "UNKNOWN")
            weight = cls.SOURCE_PRIORS.get(origin, 0.5)
            uncertainty *= (1.0 - weight)
        return 1.0 - uncertainty

    @classmethod
    def arbitrate_conflict(cls, group_a: List[Dict], group_b: List[Dict]) -> Dict[str, float]:
        """
        对冲突的两组证据进行贝叶斯裁决。
        返回：{chunk_id: final_weight}
        """
        conf_a = cls.calculate_claim_confidence(group_a)
        conf_b = cls.calculate_claim_confidence(group_b)
        
        # 归一化后验概率
        total = conf_a + conf_b
        if total == 0: return {}
        
        weight_a = conf_a / total
        weight_b = conf_b / total
        
        results = {}
        for e in group_a: results[e["id"]] = weight_a
        for e in group_b: results[e["id"]] = weight_b
        return results


class EvidenceValidationNode:
    """
     [V185.0] 证据验证节点：负责识别逻辑冲突并执行状态降权。
    """
    def __init__(self, detector=None, llm_service=None):
        from ..utils.conflict_detector import ConflictDetector
        from backend.app.services.ingestion.llm_service import llm_service as default_llm
        self.detector = detector or ConflictDetector()
        self.llm_service = llm_service or default_llm

    async def _detect_conflicts_llm(self, pool: List[Dict], query: str) -> List[Dict]:
        """
        [V280.0] 冲突探测：使用注入的探测组件。
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

        # Fallback: 如果所有证据同 source_name（如同星系），按 doc_id 拆组
        if len(source_results) < 2:
            doc_map: Dict[str, Dict] = {}
            for e in pool:
                did = str(e.get("doc_id") or "Unknown")
                if did not in doc_map:
                    doc_map[did] = {
                        "source_name": f"Doc_{did[:8]}",
                        "doc_id": did,
                        "evidence_chunks": [],
                    }
                doc_map[did]["evidence_chunks"].append(e)
            if len(doc_map) >= 2:
                source_results = list(doc_map.values())

        if len(source_results) < 2:
            return []

        return await self.detector.detect(source_results, query)

    async def audit(self, state: CourtState) -> Dict[str, Any]:
        pool = state.get("evidence_pool", [])
        if not pool:
            return {"next_step": "SYNTHESIZE"}

        print(f" [AuditorNode] 正在通过贝叶斯协议审计 {len(pool)} 条多维证据...")

        # 1. 冲突探测
        conflicts = await self._detect_conflicts_llm(pool, state.get("query", ""))
        
        # 2. 对所有证据执行来源预判（贝叶斯集合置信度）
        # 单一来源时 = SOURCE_PRIORS[origin]
        # 多证据同来源时也用先验值（真实多证据融合由冲突路径处理）
        weights = state.get("claim_weights", {})
        for e in pool:
            eid = e.get("id")
            if eid and eid not in weights:
                origin = e.get("origin", "UNKNOWN")
                weights[eid] = BayesianAggregator.SOURCE_PRIORS.get(origin, 0.5)

        # 3. 执行贝叶斯裁决
        if conflicts:
            for c in conflicts:
                # 提取参与冲突的证据组
                packages = c.get("packages", [])
                if len(packages) < 2: continue
                
                # 按照来源分组（简化版：假设前两个 package 代表两个冲突方）
                ev_a_id = packages[0].get("chunk_id")
                ev_b_id = packages[1].get("chunk_id")
                
                group_a = [e for e in pool if e["id"] == ev_a_id]
                group_b = [e for e in pool if e["id"] == ev_b_id]
                
                # 结合 LLM 的语义判定进行加权修正
                debate_results = await self._debate_and_arbitrate(c, pool, self.llm_service)
                
                # 最终执行贝叶斯融合
                bayesian_weights = BayesianAggregator.arbitrate_conflict(group_a, group_b)
                
                # 融合 LLM 判决与贝叶斯先验
                for eid, b_w in bayesian_weights.items():
                    llm_w = debate_results.get(eid, DEFAULT_WEIGHT)
                    # 联合置信度 = max(乘积, 两者最小值的50%) 防止单一低分淹没
                    combined = llm_w * b_w
                    floor = min(llm_w, b_w) * 0.5
                    weights[eid] = max(combined, floor)

        # 检查是否有不确定的冲突，需要补充侦查
        subpoena_order = self._check_uncertain_conflicts(conflicts, weights, state.get("re_harvest_count", 0))

        # 4. 物理分层建议与状态裁剪
        archive_candidates = []
        active_pool = []
        for e in pool:
            weight = weights.get(e["id"], DEFAULT_WEIGHT)
            if weight < ARCHIVE_WEIGHT_THRESHOLD:
                print(f" [AuditorNode] 证据 {e['id']} 置信度过低 ({weight:.2f})，标记为 L3 归档。")
                archive_candidates.append(e)
            else:
                #  [V185.2] 逻辑脱水：裁剪正文内容，节省 Token
                # 字段映射参考 EvidenceSchema + 下游实际消费者追踪
                pruned_e = {
                    "id": e["id"],
                    "content": "[PRUNED]",
                    "claims": e.get("claims", []),
                    "origin": e.get("origin", "UNKNOWN"),
                    "confidence": e.get("confidence", 0.0),
                    "color": e.get("color", "YELLOW"),
                    "stability": e.get("stability", 0.5),     # 保持 Schema 兼容
                    "doc_id": e.get("doc_id"),                 # 保持 Schema 兼容
                    "breadcrumb": e.get("breadcrumb", ""),
                    "page_number": e.get("page_number", 0),
                    "summary": e.get("summary", ""),           # spine_engine.py 读取
                    "is_sovereign": e.get("is_sovereign", False),  # synthesizer.py 读取
                    "source_name": e.get("source_name", "Unknown"), # adapter.py 读取
                }
                active_pool.append(pruned_e)

        print(f" [AuditorNode] 状态裁剪完成：活跃池正文已物理脱水。")

        if subpoena_order:
            # 不再自动签发补充侦查，标记为需人工仲裁
            for c in conflicts:
                c["needs_human_arbitration"] = True
                if "RED_ARBITRATION_NEEDED" not in c.get("severity", ""):
                    c["severity"] = "RED_ARBITRATION_NEEDED"
            print(f" [AuditorNode] 标记 {len(conflicts)} 处冲突为 RED_ARBITRATION_NEEDED (需人工仲裁)")
            # 走 SYNTHESIZE，让 conflicts 传递到 MCP 层供 Aily 展示

        return {
            "conflicts": conflicts,
            "claim_weights": weights,
            "evidence_pool": active_pool,
            "L3_archive": archive_candidates,
            "next_step": "SYNTHESIZE"
        }

    def _check_uncertain_conflicts(self, conflicts: List[Dict], weights: Dict, re_harvest_count: int) -> Optional[str]:
        """
        检查是否有无法确定胜负的冲突
        """
        if re_harvest_count >= MAX_SUPPLEMENTARY_SEARCHES:
            return None

        for c in conflicts:
            packages = c.get("packages", [])
            if len(packages) < 2:
                continue
            ev_ids = [p["chunk_id"] for p in packages if "chunk_id" in p]
            if len(ev_ids) < 2:
                continue
            w_a = weights.get(ev_ids[0], DEFAULT_WEIGHT)
            w_b = weights.get(ev_ids[1], DEFAULT_WEIGHT)
            if abs(w_a - w_b) < UNCERTAINTY_WEIGHT_DIFF and w_a > MIN_WEIGHT_THRESHOLD and w_b > MIN_WEIGHT_THRESHOLD:
                topic = c.get("description") or c.get("topic") or "unknown"
                return f"针对 '{topic}' 的争议需要更多证据以辅助裁决"

        return None

    async def _debate_and_arbitrate(self, conflict: Dict, pool: List[Dict], llm) -> Dict[str, float]:
        """
        模拟多代理辩论
        """
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
            logger.error(f" [AuditorNode] 质证失败: {e}")
            default_weights = {}
            if ev_a_id: default_weights[ev_a_id] = DEFAULT_WEIGHT
            if ev_b_id: default_weights[ev_b_id] = DEFAULT_WEIGHT
            return default_weights

auditor_node = EvidenceValidationNode()
