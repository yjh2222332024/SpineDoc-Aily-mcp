"""
📐 EvidenceFusionEngine - 证据融合数学引擎 (冲突感知版)
=========================================================
职责：实现基于 Dempster-Shafer 证据理论的冲突裁决算法。
特性：引入 K 因子惩罚机制，确保在逻辑严重对立时，置信度能够物理性坍缩。
"""

from typing import List, Dict, Any

class EvidenceFusionEngine:
    """
    SpineDoc 数学中枢：负责将异构证据质量 (Masses) 合成为单一置信度。
    """
    
    def __init__(self):
        self.epsilon = 1e-9
        self.last_conflict_k = 0.0 # 🚀 核心：记录最后一轮合成的冲突强度

    def combine_evidence(self, mass_functions: List[Dict[str, float]]) -> Dict[str, float]:
        """
        Dempster 组合规则
        """
        if not mass_functions:
            self.last_conflict_k = 0.0
            return {"belief": 0.0, "disbelief": 0.0, "uncertainty": 1.0}
        
        # 初始证据包
        current_m = mass_functions[0]
        self.last_conflict_k = 0.0 # 重置冲突记录
        
        for next_m in mass_functions[1:]:
            current_m = self._dempster_combine_two(current_m, next_m)
            
        return current_m

    def _dempster_combine_two(self, m1: Dict[str, float], m2: Dict[str, float]) -> Dict[str, float]:
        """
        核心公式：m(A) = (∑ m1(X) * m2(Y)) / (1 - K)
        """
        b1, d1, u1 = m1["belief"], m1["disbelief"], m1["uncertainty"]
        b2, d2, u2 = m2["belief"], m2["disbelief"], m2["uncertainty"]
        
        # 1. 计算冲突因子 K (Conflict Mass)
        # K 代表了：m1 说真且 m2 说假 + m1 说假且 m2 说真
        k = b1*d2 + d1*b2
        
        # 更新全局冲突感知 (取最大冲突点)
        self.last_conflict_k = max(self.last_conflict_k, k)
        
        # 2. 计算非冲突项
        belief_intersection = b1*b2 + b1*u2 + u1*b2
        disbelief_intersection = d1*d2 + d1*u2 + u1*d2
        uncertainty_intersection = u1*u2
        
        # 3. 归一化 (1 - K)
        if k >= 1.0 - self.epsilon:
            return {"belief": 0.0, "disbelief": 0.0, "uncertainty": 0.0, "conflict_alert": True}
        
        normalization = 1.0 - k
        
        return {
            "belief": round(belief_intersection / normalization, 4),
            "disbelief": round(disbelief_intersection / normalization, 4),
            "uncertainty": round(uncertainty_intersection / normalization, 4)
        }

    def get_final_score(self, fused_m: Dict[str, float]) -> float:
        """
        V9.2 科学置信度公式：
        Confidence = (Belief + 0.3 * Uncertainty) * (1 - last_conflict_k)
        """
        if fused_m.get("conflict_alert") or self.last_conflict_k > 0.98:
            return 0.0 # 无法调和的绝对冲突
            
        raw_score = fused_m["belief"] + 0.3 * fused_m["uncertainty"]
        
        # 🚀 物理抑制：吵得越凶，最终分数降得越快
        # 这是一个线性抑制项，确保在 K=0.72 时，分数会被大幅削减
        final_score = raw_score * (1.0 - self.last_conflict_k)
        
        return round(final_score, 4)
