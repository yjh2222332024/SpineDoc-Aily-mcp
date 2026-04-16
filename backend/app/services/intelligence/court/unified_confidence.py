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
    4. Moderator 明确裁决冲突

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

        # 条件 3: Moderator 已裁决冲突
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


class UnifiedConfidenceCalculator:
    """
    ⚖️ 统一置信度计算器

    支持本地 PDF 和联网证据的统一评估，允许严苛条件下推翻本地证据。
    """

    def __init__(self, custom_percentiles: Optional[Dict] = None):
        """
        初始化计算器

        Args:
            custom_percentiles: 自定义分位数阈值
        """
        self.color_calc = ColorConfidenceCalculator(custom_percentiles)
        self.integrity_checker = LocalEvidenceIntegrityChecker()

    def calculate_local(
        self,
        chunk: Dict,
        web_evidence: Optional[List[Dict]] = None
    ) -> Tuple[ConfidenceColor, float]:
        """
        计算本地 PDF 证据置信度（可能被联网证据推翻）

        Args:
            chunk: 本地证据分片 {
                content: str,
                page_number: int,
                breadcrumb: str,
                pdf_creation_date: Optional[str],
                doc_status: str,  # 'completed' | 'pending'
                has_conflict_verdict: bool,
                ...
            }
            web_evidence: 相关联网证据列表

        Returns:
            (颜色，置信度 0-1)
        """
        # 1. 计算基础置信度（本地来源）
        w_source = self._calculate_local_source_score(chunk)
        w_recency = self._calculate_local_recency(chunk, web_evidence)
        w_corroboration = self._calculate_corroboration(chunk, source_type='LOCAL_PDF')

        # 基础置信度
        base_score = w_source * w_recency * w_corroboration

        # 2. 检查是否被推翻
        is_overridden = False
        if web_evidence and self.integrity_checker.should_override_local(chunk, web_evidence):
            is_overridden = True
            base_score = base_score * self.integrity_checker.integrity_penalty  # 置信度减半

        # 3. 颜色判定
        color = self._determine_color(base_score, is_overridden)

        # 4. 标记状态
        chunk['color'] = color.value
        chunk['confidence'] = round(base_score, 3)
        chunk['is_overridden'] = is_overridden

        return color, round(base_score, 3)

    def calculate_web(
        self,
        chunk: Dict,
        independent_sources: int = 1
    ) -> Tuple[ConfidenceColor, float]:
        """
        计算联网证据置信度

        Args:
            chunk: 联网证据分片 {
                content: str,
                source_url: str,
                published_date: Optional[str],
                query_type: str,
                ...
            }
            independent_sources: 独立来源数

        Returns:
            (颜色，置信度 0-1)
        """
        # 使用原有颜色计算器
        color, score = self.color_calc.calculate(chunk, independent_sources)

        # 标记状态
        chunk['color'] = color.value
        chunk['confidence'] = score

        return color, score

    def _calculate_local_source_score(self, chunk: Dict) -> float:
        """
        计算本地 PDF 来源可信度

        基于：
        1. 文档入库状态（completed/pending）
        2. TOC 完整性（有目录 > 无目录）
        3. 分片位置（核心章节 > 附录）
        """
        base_score = 0.85  # 入库文档基础分

        # 状态加成
        if chunk.get('doc_status') == 'completed':
            base_score += 0.10

        # TOC 完整性加成
        if chunk.get('breadcrumb'):
            base_score += 0.05

        # 核心章节加成（breadcrumb 包含"第 X 章"）
        breadcrumb = chunk.get('breadcrumb', '')
        if '第' in breadcrumb and '章' in breadcrumb:
            base_score += 0.05

        return min(1.0, base_score)

    def _calculate_local_recency(
        self,
        chunk: Dict,
        web_evidence: Optional[List[Dict]]
    ) -> float:
        """
        计算本地 PDF 内容时间衰减

        策略：
        1. 优先使用 PDF 元数据（creation_date）
        2. 若无，用外部证据推断
        3. 若都无，保守估计
        """
        # 1. PDF 元数据
        pub_date_str = chunk.get('pdf_creation_date')

        if pub_date_str:
            try:
                pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                days_old = (datetime.now().astimezone() - pub_date).days

                # 学术 PDF 半衰期 3 年
                lambda_ = math.log(2) / (365 * 3)
                return math.exp(-lambda_ * days_old)
            except:
                pass

        # 2. 外部证据推断
        if web_evidence:
            conflicting_web = [
                e for e in web_evidence
                if e.get('published_date') and e.get('source_url')
            ]

            if conflicting_web:
                latest_date = max(e['published_date'] for e in conflicting_web if e.get('published_date'))
                try:
                    latest = datetime.fromisoformat(latest_date.replace("Z", "+00:00"))
                    days_old = (datetime.now().astimezone() - latest).days

                    # 有冲突时半衰期缩短为 1 年
                    lambda_ = math.log(2) / 365
                    return math.exp(-lambda_ * days_old) * 0.7  # 冲突惩罚
                except:
                    pass

        # 3. 保守估计
        return 0.60

    def _calculate_corroboration(self, chunk: Dict, source_type: str) -> float:
        """
        计算多源印证加成

        跨源印证（本地 + 联网）加成更高
        """
        # 简单实现：假设已有 independent_sources 字段
        independent_sources = chunk.get('independent_sources', 1)

        # 基础加成
        w = 1.0 - (1.0 / independent_sources)
        w = min(0.8, w)
        base_multiplier = 1.0 + (w * 0.3)

        # 跨源加成
        source_types = chunk.get('source_types', [source_type])
        has_local = 'LOCAL_PDF' in source_types
        has_web = 'INTERNET' in source_types

        if has_local and has_web:
            # 🚀 [V50.10] 从配置读取跨源加成系数
            bonus = settings.COURT_AUTHORITY_CROSS_SOURCE_BONUS
            return base_multiplier * bonus

        return base_multiplier

    def _determine_color(self, score: float, is_overridden: bool) -> ConfidenceColor:
        """
        颜色判定

        被推翻的本地证据自动降级
        """
        if is_overridden:
            # 被推翻的本地证据，最高 YELLOW
            if score >= 0.45:
                return ConfidenceColor.YELLOW
            elif score >= 0.25:
                return ConfidenceColor.YELLOW
            else:
                return ConfidenceColor.RED

        # 正常判定
        if score >= 0.70:
            return ConfidenceColor.GREEN
        elif score >= 0.50:
            return ConfidenceColor.BLUE
        elif score >= 0.25:
            return ConfidenceColor.YELLOW
        else:
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
