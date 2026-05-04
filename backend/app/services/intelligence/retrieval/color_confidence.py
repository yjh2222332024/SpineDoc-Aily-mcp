import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlparse

from backend.app.services.intelligence.retrieval.utils.confidence_models import AuthorityModel, DecayModel


class ConfidenceColor(str, Enum):
    GREEN = "GREEN"
    BLUE = "BLUE"
    YELLOW = "YELLOW"
    RED = "RED"


@dataclass
class DomainStats:
    h5_index: Optional[int] = None
    alexa_rank: Optional[int] = None
    peer_reviewed: bool = False
    user_generated: bool = False
    code_verifiable: bool = False


COLOR_ICONS = {
    ConfidenceColor.GREEN: "🟢",
    ConfidenceColor.BLUE: "🔵",
    ConfidenceColor.YELLOW: "🟡",
    ConfidenceColor.RED: "🔴",
}

COLOR_LABELS = {
    ConfidenceColor.GREEN: "AUTHORITATIVE",
    ConfidenceColor.BLUE: "VERIFIED",
    ConfidenceColor.YELLOW: "UNVERIFIED",
    ConfidenceColor.RED: "CONFLICT",
}

COLOR_DESCRIPTIONS = {
    ConfidenceColor.GREEN: "权威来源 + 多源印证，可直接引用",
    ConfidenceColor.BLUE: "多源交叉验证，可信",
    ConfidenceColor.YELLOW: "单一来源，需进一步验证",
    ConfidenceColor.RED: "检测到冲突，需人工介入",
}

# 稳定性锚定阈值
STABILITY_ANCHOR_THRESHOLD = 0.8
STABILITY_FLOOR_THRESHOLD = 0.95
DEFAULT_STABILITY = 0.5

# 评分权重
AUTH_WEIGHT = 0.8
CORROB_WEIGHT = 0.2

# 默认百分位
DEFAULT_PERCENTILES = {'GREEN': 0.65, 'BLUE': 0.45, 'YELLOW': 0.25}

logger = logging.getLogger(__name__)

class ColorConfidenceCalculator:
    """
    🎨 重构后的四色置信度计算器 (V2.0)
    职责：编排各个评分模型，决定证据最终的‘颜色’。
    """
    def __init__(self, registry=None):
        # 🛡️ 架构师纪律：通过 Registry 或注入来获取配置，避免模块顶层加载
        from .config_loader import get_config_loader
        loader = get_config_loader()
        
        self.authority_model = AuthorityModel(loader.get_domain_base_scores())
        self.decay_model = DecayModel(loader.get_query_half_life())
        self.percentiles = loader.get_color_percentiles()
        self.domain_stats = loader.get_domain_stats()

    def calculate(
        self,
        chunk: Dict,
        source_count: int = 1,
        independent_sources: int = 1,
        has_conflict: bool = False
    ) -> Tuple[ConfidenceColor, float]:
        """
        核心判定逻辑：引入稳定性锚定。
        """
        # 1. 冲突判定
        if has_conflict:
            return ConfidenceColor.RED, 0.0

        # 2. 维度评分
        domain = urlparse(chunk.get('source_url', '')).netloc
        stats_raw = self.domain_stats.get(domain)
        stats = DomainStats(**stats_raw) if stats_raw else None
        
        w_auth = self.authority_model.get_score(domain, stats)
        
        # 🚀 [V175.0] 主权修正：稳定性锚定 (Stability Anchoring)
        stability = float(chunk.get('stability', DEFAULT_STABILITY))
        if stability >= STABILITY_ANCHOR_THRESHOLD:
            # 🛡️ 架构师守则：稳定知识不随时间腐烂
            w_recency = 1.0
            print(f"⚓ [Confidence] Stability Anchor Active ({stability:.2f}) -> Suppressing time decay.")
        else:
            w_recency = self.decay_model.calculate_decay(
                chunk.get('published_date'),
                chunk.get('query_type', 'RESEARCH')
            )

        w_corrob = 1 - (1 / independent_sources) if independent_sources > 0 else 0.5

        # 3. 综合计算 (稳定性加权)
        final_score = w_auth * w_recency * (AUTH_WEIGHT + CORROB_WEIGHT * w_corrob)

        # 如果稳定性极高，强行保底分
        if stability >= STABILITY_FLOOR_THRESHOLD:
            final_score = max(final_score, STABILITY_FLOOR_THRESHOLD)

        # 4. 颜色映射
        color = self._map_to_color(final_score)
        return color, round(final_score, 3)

    def _map_to_color(self, score: float) -> ConfidenceColor:
        green_threshold = self.percentiles.get('GREEN') or DEFAULT_PERCENTILES['GREEN']
        blue_threshold = self.percentiles.get('BLUE') or DEFAULT_PERCENTILES['BLUE']
        yellow_threshold = self.percentiles.get('YELLOW') or DEFAULT_PERCENTILES['YELLOW']

        if score >= green_threshold: return ConfidenceColor.GREEN
        if score >= blue_threshold: return ConfidenceColor.BLUE
        if score >= yellow_threshold: return ConfidenceColor.YELLOW
        return ConfidenceColor.RED
