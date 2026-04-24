"""
🏛️ Protocol Parser - 协议解析模块
===================================
统一的协议解析接口，支持多种格式输入。

使用示例:
    from backend.app.services.protocol_parser import parse_protocol

    ir = parse_protocol("protocol.anb")
    print(ir.participants)  # ["A", "B", "S"]
"""

from pathlib import Path
from .ir import ProtocolIR
from .scheduler import ProtocolParserScheduler, get_scheduler


def parse_protocol(file_path: str | Path) -> ProtocolIR:
    """
    解析协议文件并返回 ProtocolIR

    Args:
        file_path: 文件路径（支持 .anb, .spthy, .txt, .md, .pdf）

    Returns:
        ProtocolIR 对象

    Raises:
        ValueError: 当文件格式不支持时
        FileNotFoundError: 当文件不存在时

    示例:
        >>> ir = parse_protocol("protocols/needham_schroeder.anb")
        >>> print(ir.protocol_id)
        'needham_schroeder'
        >>> print(ir.participants)
        ['A', 'B', 'S']
    """
    if isinstance(file_path, str):
        file_path = Path(file_path)

    scheduler = get_scheduler()
    return scheduler.parse(file_path)


__all__ = [
    # 核心类
    "ProtocolParserScheduler",
    "ProtocolIR",
    # 便捷函数
    "parse_protocol",
]
