"""
⚖️ 统一置信度计算器 (Unified Confidence Calculator)
=====================================================
基于第一性原理，统一计算本地 PDF 和联网证据的置信度。

核心洞察：
1. 本地证据不是绝对可信 —— 它可能过时
2. 允许联网证据推翻本地证据，但条件必须严苛
3. 跨源印证（本地 + 联网）> 单一来源

数学模型：
W_final = W_source × W_recency × W_corroboration × W_integrity

配置说明：
- 权威来源列表：backend/storage/domain_whitelist.json
- 覆盖条件：backend/storage/confidence_config.json
"""

import math
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from urllib.parse import urlparse
from enum import Enum

from .color_confidence import (
    ConfidenceColor,
    ColorConfidenceCalculator,
    DOMAIN_BASE_SCORES,
    QUERY_HALF_LIFE
)
from backend.app.core.config import settings
from .config_loader import get_config_loader


# 🏛️ 权威来源列表（从配置文件加载）
def _load_authoritative_sources() -> list:
    loader = get_config_loader()
    return loader.get_authoritative_sources()


# 🏛️ 域名稳定性映射（从配置文件加载）
def _load_domain_stability() -> Dict[str, float]:
    loader = get_config_loader()
    return loader.get_domain_stability()


AUTHORITATIVE_SOURCES = _load_authoritative_sources()
DOMAIN_STABILITY = _load_domain_stability()


class LocalEvidenceIntegrityChecker:
    """
    🛡️ 本地证据完整性检查器

    推翻条件（必须全部满足）：
    1. 联网证据来自权威来源（≥2 个）
    2. 联网证据时间更新（晚于本地 PDF 元数据）
    3. 多源印证（≥2 个独立联网来源）
    4. ConflictResolver 明确裁决冲突

    配置参数：
    - min_authoritative_sources: 最小权威来源数（默认 2）
    - integrity_penalty: 置信度惩罚系数（默认 0.5）
    """

    def __init__(self):
        loader = get_config_loader()
        self.min_authoritative_sources = loader.get_min_authoritative_sources()
        self.integrity_penalty = loader.get_integrity_penalty()

    def should_override_local(
        self,
        local_chunk: Dict,
        web_evidence: List[Dict]
    ) -> bool:
        """
        判断是否应该用联网证据推翻本地证据

        Args:
            local_chunk: 本地证据分片
            web_evidence: 联网证据列表

        Returns:
            bool: 是否应该推翻
        """
        # 条件 1: 权威来源（≥2 个）
        authoritative_evidence = [
            e for e in web_evidence
            if self._is_authoritative_source(e.get('source_url', ''))
        ]
        if len(authoritative_evidence) < self.min_authoritative_sources:
            return False

        # 条件 2: 时间更新
        local_date = local_chunk.get('pdf_creation_date')
        if not local_date:
            # 本地证据无元数据，无法判断时间先后
            return False

        web_dates = [
            e['published_date']
            for e in authoritative_evidence
            if e.get('published_date')
        ]
        if not web_dates:
            return False

        latest_web_date = max(web_dates)
        if latest_web_date <= local_date:
            # 联网证据不更新
            return False

        # 条件 3: ConflictResolver 已裁决冲突
        if not local_chunk.get('has_conflict_verdict', False):
            return False

        # 全部条件满足，允许推翻
        return True

    def _is_authoritative_source(self, url: str) -> bool:
        """判断是否为权威来源"""
        if not url:
            return False
        domain = urlparse(url).netloc
        return any(s in domain for s in AUTHORITATIVE_SOURCES)


import math
import logging
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timezone
from urllib.parse import urlparse
from enum import Enum

from .color_confidence import ConfidenceColor
from backend.app.core.config import settings
from .config_loader import get_config_loader
from backend.app.infra.math.evidence_fusion import EvidenceFusionEngine
from backend.app.infra.math.velocity_stats import LogicalMetabolismStats

logger = logging.getLogger(__name__)

class UnifiedConfidenceCalculator:
    """
    ⚖️ 统一置信度计算器 (V9.2 科学版)
    
    职责：
    1. 利用 LogicalMetabolismStats 感知各领域的“知识半衰期”。
    2. 利用 EvidenceFusionEngine (Dempster-Shafer) 融合异构证据。
    3. 消除硬编码，实现物理级置信度对齐。
    """

    def __init__(self, session):
        self.fusion_engine = EvidenceFusionEngine()
        self.stats_engine = LogicalMetabolismStats(session)
        self.config = get_config_loader()

    async def calculate(
        self,
        local_chunk: Dict,
        web_evidence: List[Dict],
        cluster_id: str
    ) -> Tuple[ConfidenceColor, float]:
        """
        🚀 Core logic: Fuse local evidence with web evidence using Dempster-Shafer theory.
        """
        # 1. 为本地证据分配初始 Mass (基于主权等级)
        local_mass = await self._allocate_local_mass(local_chunk, cluster_id)
        
        # 2. 为联网证据分配初始 Mass (应用二级冲突探测)
        web_masses = []
        for e in web_evidence:
            # 🚀 [V9.3 核心改进]：二级探测流水线
            is_contradiction = await self._detect_conflict_tier(local_chunk, e)
            
            mass = self._allocate_web_mass(e, is_contradiction)
            web_masses.append(mass)
        
        # 3. 证据融合 (Dempster-Shafer Fusion)
        all_masses = [local_mass] + web_masses
        fused_m = self.fusion_engine.combine_evidence(all_masses)
        
        # 4. 获取物理抑制后的最终分数
        final_score = self.fusion_engine.get_final_score(fused_m)
        
        # 5. 映射颜色
        color = self._determine_color_v9(final_score, self.fusion_engine.last_conflict_k)
        
        # 回填元数据供前端显示
        local_chunk['confidence'] = final_score
        local_chunk['color'] = color.value
        local_chunk['conflict_k'] = self.fusion_engine.last_conflict_k
        
        return color, final_score

    async def _detect_conflict_tier(self, local: Dict, web: Dict) -> bool:
        """
        ⚖️ 二级冲突探测流水线：机械 > LLM
        """
        # --- TIER 1: 机械硬核探测 (Mechanistic) ---
        web_content = web.get('content', '').lower()
        web_label = (web.get('label') or '').upper()
        local_label = (local.get('label') or '').upper()

        # 1. 证明结果硬对线 (Tamarin 官方判决)
        if "FALSIFIED" in web_label and "VERIFIED" in local_label:
            return True
            
        # 2. 漏洞级关键词探测
        hard_conflict_keywords = ["漏洞", "leak", "compromised", "attack found", "falsified", "exploit"]
        if any(kw in web_content for kw in hard_conflict_keywords):
            return True

        # --- TIER 2: LLM 语义公诉人 (Neural Fallback) ---
        # 只有在机械探测无法断定时触发
        try:
            # 未来这里通过 slm_swarm.conflict_check(local, web) 实现
            # 目前模拟：如果 web 带有明确的 contradiction 标志
            return web.get('llm_verdict') == "contradiction"
        except:
            return False

    async def _allocate_local_mass(self, chunk: Dict, cluster_id: str) -> Dict[str, float]:
        """Calculate local mass with adaptive time decay."""
        base_belief = 0.90

        tau = await self.stats_engine.get_sector_velocity(cluster_id)
        
        # 🚀 物理对齐：确保时间轴统一
        pub_date_raw = chunk.get('pdf_creation_date')
        if not pub_date_raw:
            pub_date = datetime.now(timezone.utc)
        elif isinstance(pub_date_raw, str):
            from dateutil import parser
            pub_date = parser.isoparse(pub_date_raw)
        else:
            pub_date = pub_date_raw

        # 如果是 naive，强制补上 UTC；如果是 aware，保留其时区
        if pub_date.tzinfo is None:
            pub_date = pub_date.replace(tzinfo=timezone.utc)
            
        time_diff = (datetime.now(timezone.utc) - pub_date).total_seconds()
        
        # 🚀 应用科学衰减模型: W = e^(-Δt / τ)
        decay_weight = self.stats_engine.calculate_decay_weight(time_diff, tau)
        
        final_belief = base_belief * decay_weight
        
        return {
            "belief": round(final_belief, 4),
            "disbelief": 0.0,
            "uncertainty": round(1.0 - final_belief, 4)
        }

    def _allocate_web_mass(self, e: Dict, is_contradiction: bool = False) -> Dict[str, float]:
        """计算联网证据 Mass"""
        # 🚀 [V9.4 核心改进]：优先尊重证据自带的原始置信度
        base_weight = e.get('confidence', 0.70)
        
        # 权威度加成
        url = e.get('source_url', '') or e.get('source', '')
        domain = urlparse(url).netloc
        
        authoritative_sources = self.config.get_authoritative_sources()
        if any(s in domain for s in AUTHORITATIVE_SOURCES):
            # 只有在原始权重不是特别低的情况下才加成
            if base_weight > 0.4:
                base_weight += 0.15 
            
        final_m = min(0.95, round(base_weight, 4))
        
        # 极性分配逻辑
        if is_contradiction:
            return {
                "belief": 0.0,
                "disbelief": final_m,
                "uncertainty": round(1.0 - final_m, 4)
            }
        else:
            return {
                "belief": final_m,
                "disbelief": 0.0,
                "uncertainty": round(1.0 - final_m, 4)
            }

    def _determine_color_v9(self, score: float, k: float) -> ConfidenceColor:
        """
        V9.2 颜色判定：增加冲突感知
        """
        if k > 0.8: return ConfidenceColor.RED # 极度冲突
        
        if score >= 0.80: return ConfidenceColor.GREEN
        if score >= 0.60: return ConfidenceColor.BLUE
        if score >= 0.35: return ConfidenceColor.YELLOW
        return ConfidenceColor.RED


# 🎨 渲染辅助
def render_evidence_with_color(chunk: Dict) -> str:
    """
    渲染带颜色的证据（用于 CLI/Web）
    """
    from .color_confidence import COLOR_ICONS, COLOR_LABELS, COLOR_DESCRIPTIONS

    color = chunk.get('color', 'YELLOW')
    confidence = chunk.get('confidence', 0.0)
    source_type = chunk.get('type', 'UNKNOWN')

    icon = COLOR_ICONS.get(ConfidenceColor(color), '🟡')
    label = COLOR_LABELS.get(ConfidenceColor(color), 'UNKNOWN')
    desc = COLOR_DESCRIPTIONS.get(ConfidenceColor(color), '')

    # 被推翻标记
    override_flag = ' ⚠️ 已推翻' if chunk.get('is_overridden') else ''

    if source_type == 'LOCAL_PDF':
        source = f"本地 PDF P{chunk.get('page_number', '?')}"
    else:
        source = f"{urlparse(chunk.get('source_url', '')).netloc}"

    return f"{icon} {label} ({confidence:.2f}) | {source}{override_flag}\n   {desc}"
