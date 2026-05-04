"""
置信度评分计算模块
通过 ColorConfidenceCalculator 委托执行计算逻辑
"""
import logging
from typing import Dict, Tuple

from .color_confidence import ColorConfidenceCalculator, ConfidenceColor

logger = logging.getLogger(__name__)


def calculate(
    chunk: Dict,
    source_count: int = 1,
    independent_sources: int = 1,
    has_conflict: bool = False,
    calculator: ColorConfidenceCalculator = None
) -> Tuple[ConfidenceColor, float]:
    """
    置信度评分计算入口
    委托给 ColorConfidenceCalculator 执行
    """
    if calculator is None:
        calculator = ColorConfidenceCalculator()

    return calculator.calculate(
        chunk=chunk,
        source_count=source_count,
        independent_sources=independent_sources,
        has_conflict=has_conflict
    )