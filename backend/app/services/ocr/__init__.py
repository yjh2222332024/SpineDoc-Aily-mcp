"""
SpineDoc OCR 模块

支持纯图 PDF 的目录提取和内容识别
"""

from .integration.architect_parser import ArchitectVisualParser

__all__ = [
    # 解析器
    "ArchitectVisualParser",
]
