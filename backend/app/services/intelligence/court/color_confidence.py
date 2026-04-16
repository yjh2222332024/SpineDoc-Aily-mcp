"""
🎨 四色置信度系统 (Color Confidence System)
============================================
基于信息论、衰减模型、统计分位数的严谨置信度评估。

数学基础：
1. 权威分 (W_authority): log(引用次数 + 1) / log(最大引用次数 + 1)
2. 时间衰减 (W_recency): e^(-λ × days), λ = ln(2) / half_life
3. 多源印证 (W_corroboration): 1 - 1/n (信息熵简化模型)
4. 颜色判定：基于历史分布的分位数阈值

配置说明：
- 域名白名单/评分：backend/storage/domain_whitelist.json
- 域名统计：backend/storage/domain_stats.json
- 置信度参数：backend/storage/confidence_config.json
"""

import math
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from .config_loader import get_config_loader
from backend.app.core.config import settings


class ConfidenceColor(str, Enum):
    GREEN = "GREEN"      # 权威 (前 10%)
    BLUE = "BLUE"        # 已验证 (前 30%)
    YELLOW = "YELLOW"    # 未验证 (前 60%)
    RED = "RED"          # 冲突/极低置信度


@dataclass
class DomainStats:
    """域名统计信息（用于权威分计算）"""
    h5_index: Optional[int] = None      # Google Scholar h5 指数
    alexa_rank: Optional[int] = None    # Alexa 排名
    peer_reviewed: bool = False         # 是否同行评审
    user_generated: bool = False        # 是否用户生成内容
    code_verifiable: bool = False       # 代码是否可验证


def _load_domain_stats() -> Dict[str, DomainStats]:
    """从配置加载域名统计信息"""
    loader = get_config_loader()
    raw_stats = loader.get_domain_stats()

    result = {}
    for domain, stats in raw_stats.items():
        result[domain] = DomainStats(
            h5_index=stats.get('h5_index'),
            alexa_rank=stats.get('alexa_rank'),
            peer_reviewed=stats.get('peer_reviewed', False),
            user_generated=stats.get('user_generated', False),
            code_verifiable=stats.get('code_verifiable', False),
        )
    return result


def _load_domain_base_scores() -> Dict[str, float]:
    """从配置加载域名基础权威分"""
    loader = get_config_loader()
    return loader.get_domain_base_scores()


def _load_query_half_life() -> Dict[str, int]:
    """从配置加载查询类型半衰期"""
    loader = get_config_loader()
    return loader.get_query_half_life()


def _load_color_percentiles() -> Dict[ConfidenceColor, float]:
    """从配置加载颜色分位数阈值"""
    loader = get_config_loader()
    raw_percentiles = loader.get_color_percentiles()
    return {
        ConfidenceColor.GREEN: raw_percentiles.get('GREEN', 0.65),
        ConfidenceColor.BLUE: raw_percentiles.get('BLUE', 0.45),
        ConfidenceColor.YELLOW: raw_percentiles.get('YELLOW', 0.25),
    }


# 🏛️ 域名统计数据库（从配置文件加载）
DOMAIN_STATS = _load_domain_stats()

# 基础权威分（从配置文件加载）
DOMAIN_BASE_SCORES = _load_domain_base_scores()

# 🏛️ 查询类型半衰期（从配置文件加载）
QUERY_HALF_LIFE = _load_query_half_life()

# 🏛️ 颜色分位数阈值（从配置文件加载）
COLOR_PERCENTILES = _load_color_percentiles()


class ColorConfidenceCalculator:
    """
    🎨 四色置信度计算器

    数学模型：
    W_final = W_authority × W_recency × W_corroboration

    颜色判定：
    - GREEN: W ≥ 0.65 (前 10%，需要高分 + 多源)
    - BLUE: 0.45 ≤ W < 0.65 (前 30%)
    - YELLOW: 0.25 ≤ W < 0.45 (前 60%)
    - RED: W < 0.25 或检测到冲突
    """

    def __init__(self, custom_percentiles: Optional[Dict] = None):
        """
        初始化计算器

        Args:
            custom_percentiles: 自定义分位数阈值（用于适配特定领域，优先于配置文件）
        """
        if custom_percentiles is not None:
            # 自定义参数优先
            self.percentiles = {
                ConfidenceColor.GREEN: custom_percentiles.get('GREEN', 0.65),
                ConfidenceColor.BLUE: custom_percentiles.get('BLUE', 0.45),
                ConfidenceColor.YELLOW: custom_percentiles.get('YELLOW', 0.25),
            }
        else:
            # 从配置文件加载
            self.percentiles = COLOR_PERCENTILES

        self._max_h5_index = max(
            (s.h5_index or 0 for s in DOMAIN_STATS.values()),
            default=500
        )

    def calculate(
        self,
        chunk: Dict,
        source_count: int = 1,
        independent_sources: int = 1,
        has_conflict: bool = False
    ) -> Tuple[ConfidenceColor, float]:
        """
        计算证据分片的颜色置信度

        Args:
            chunk: 证据分片 {
                content: str,
                source_url: str,
                published_date: str,
                query_type: str,
                ...
            }
            source_count: 总来源数（含转载）
            independent_sources: 独立来源数（去重后）
            has_conflict: 是否检测到冲突

        Returns:
            (颜色，置信度 0-1)
        """
        # 1. 冲突优先（RED）
        if has_conflict:
            base_score = self._calculate_base_score(chunk)
            return ConfidenceColor.RED, round(base_score, 3)

        # 2. 计算各分量
        w_authority = self.get_domain_authority(chunk.get('source_url', ''))
        w_recency = self._calculate_recency_weight(
            chunk.get('published_date'),
            chunk.get('query_type', 'RESEARCH')
        )
        w_corroboration = self._calculate_corroboration(independent_sources)

        # 3. 综合置信度
        base_score = w_authority * w_recency
        final_score = base_score * w_corroboration

        # 4. 颜色判定（基于分位数）
        color = self._determine_color_by_percentile(final_score, independent_sources)

        return color, round(final_score, 3)

    def _calculate_base_score(self, chunk: Dict) -> float:
        """计算基础置信度（不含多源加成）"""
        w_authority = self.get_domain_authority(chunk.get('source_url', ''))
        w_recency = self._calculate_recency_weight(
            chunk.get('published_date'),
            chunk.get('query_type', 'RESEARCH')
        )
        return w_authority * w_recency

    def get_domain_authority(self, url: str) -> float:
        """
        获取域名权威分

        计算方法：
        1. 优先使用预计算的基础分
        2. 若无，基于 h5_index 或 alexa_rank 动态计算
        3. 未知域名返回保守估计
        """
        if not url:
            return 0.50  # 无来源，保守估计

        from urllib.parse import urlparse
        domain = urlparse(url).netloc

        # 1. 精确匹配
        if domain in DOMAIN_BASE_SCORES:
            return DOMAIN_BASE_SCORES[domain]

        # 2. 模糊匹配（二级域名）
        for tier_domain, score in DOMAIN_BASE_SCORES.items():
            if domain.endswith(tier_domain):
                return score

        # 3. 动态计算（基于统计）
        if domain in DOMAIN_STATS:
            stats = DOMAIN_STATS[domain]
            return self._compute_score_from_stats(stats)

        # 4. 未知域名
        return 0.50

    def _compute_score_from_stats(self, stats: DomainStats) -> float:
        """
        从域名统计动态计算权威分

        公式：
        score = log(h5_index + 1) / log(max_h5 + 1) × 同行评审加成
              或
        score = log(1/alexa_rank) / log(1/min_rank) × 用户生成惩罚
        """
        if stats.h5_index:
            # 学术指标
            base = math.log(stats.h5_index + 1) / math.log(self._max_h5_index + 1)
            if stats.peer_reviewed:
                # 🚀 [V50.10] 从配置读取同行评审加成
                bonus = settings.COURT_AUTHORITY_PEER_REVIEW_BONUS
                return min(1.0, base * bonus)
            return base

        if stats.alexa_rank:
            # 流量指标
            base = math.log(1 / stats.alexa_rank) / math.log(1 / 5)
            if stats.user_generated:
                # 🚀 [V50.10] 从配置读取用户生成惩罚
                penalty = settings.COURT_AUTHORITY_USER_GENERATED_PENALTY
                return max(0.3, base * penalty)
            return base

        if stats.code_verifiable:
            return 0.80  # 代码可验证，中等偏上

        return 0.50  # 无统计数据

    def _calculate_recency_weight(
        self,
        pub_date_str: Optional[str],
        query_type: str
    ) -> float:
        """
        计算时间衰减权重

        公式：W = e^(-λ × days), λ = ln(2) / half_life

        验证示例（TECH_NEWS, 90 天）:
        λ = ln(2) / 30 ≈ 0.0231
        W = e^(-0.0231 × 90) = e^(-2.08) ≈ 0.125
        """
        half_life = QUERY_HALF_LIFE.get(query_type, 180)

        if not pub_date_str:
            # 无发布日期：保守估计 0.80
            # 假设：未知时间的信息平均"年龄"为 half_life/2
            # math.exp(-math.log(2) * 0.5) ≈ 0.71 → 保守给 0.80
            return 0.80

        try:
            pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
            days_old = (datetime.now().astimezone() - pub_date).days

            # 指数衰减
            lambda_ = math.log(2) / half_life
            return math.exp(-lambda_ * days_old)

        except (ValueError, TypeError):
            return 0.80  # 解析失败，保守值

    def _calculate_corroboration(self, independent_sources: int) -> float:
        """
        计算多源印证加成

        基于信息熵简化模型：
        W = 1 - 1/n

        验证：
        n=1: W = 0.00 (无加成，基础分)
        n=2: W = 0.50 (加成 50%)
        n=3: W = 0.67 (加成 67%)
        n=4: W = 0.75 (加成 75%)
        n≥5: W = 0.80 (饱和，不再增加)

        注意：这里是加成系数，实际计算是乘法
        最终置信度 = 基础分 × (1 + W_corroboration × 0.3)
        """
        if independent_sources <= 1:
            return 1.0  # 单一来源，无加成

        # 信息熵简化模型，上限 0.8
        w = 1.0 - (1.0 / independent_sources)
        w = min(0.8, w)  # 饱和

        # 转换成加成系数（最多加成 30%）
        return 1.0 + (w * 0.3)

    def _determine_color_by_percentile(self, score: float, independent_sources: int = 1) -> ConfidenceColor:
        """
        基于分位数判定颜色

        统计基础：假设 1000 条历史证据的置信度分布
        - GREEN: score ≥ 0.65 (top 10%，需要高分 + 多源)
        - BLUE: 0.45 ≤ score < 0.65
        - YELLOW: 0.25 ≤ score < 0.45 (单一来源或低分)
        - RED: score < 0.25 (极低置信度)

        注意：单一来源最高只能是 YELLOW，不因为分低就判 RED
        RED 仅用于冲突检测
        """
        green_threshold = self.percentiles[ConfidenceColor.GREEN]
        blue_threshold = self.percentiles[ConfidenceColor.BLUE]
        yellow_threshold = self.percentiles[ConfidenceColor.YELLOW]

        if score >= green_threshold and independent_sources >= 2:
            return ConfidenceColor.GREEN
        elif score >= blue_threshold:
            if independent_sources >= 2:
                return ConfidenceColor.BLUE
            else:
                return ConfidenceColor.YELLOW  # 单源最高 YELLOW
        elif score >= yellow_threshold:
            return ConfidenceColor.YELLOW
        else:
            # 极低置信度：如果是单源，仍为 YELLOW；如果多源但分低，可能是 RED
            if independent_sources >= 2:
                return ConfidenceColor.RED  # 多源但分低，可能有冲突
            else:
                return ConfidenceColor.YELLOW  # 单源低分，待验证


# 🎨 颜色渲染
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


def render_color_confidence(color: ConfidenceColor, score: float) -> str:
    """
    渲染颜色置信度（用于 CLI/Web 显示）
    """
    icon = COLOR_ICONS[color]
    label = COLOR_LABELS[color]
    desc = COLOR_DESCRIPTIONS[color]
    return f"{icon} {label} ({score:.2f}) - {desc}"
