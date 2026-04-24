"""
🛡️ SpineDoc Interfaces Facade - 接口总线
========================================
遵循 Clean Architecture，定义各模块间的主权契约。
"""

from .auditor import ISpineAuditor
from .memory import IAgenticMemory
from .reporter import IFeishuReporter

# Legacy Aliases
SpineReporter = IFeishuReporter

# 默认空实现 (Null Objects)
from typing import Dict, Any, List

class NullReporter(IFeishuReporter):
    async def report_verdict(self, verdict: Dict[str, Any], chat_id: str) -> bool: return True
    async def sync_asset(self, verdict: Dict[str, Any], evolution_logs: Dict[str, Any]) -> bool: return True

class NullMemory(IAgenticMemory):
    async def ingest_memory(self, chunk_data: Dict[str, Any]) -> str: return ""
    async def evolve_network(self, node_id: str) -> List[Dict[str, Any]]: return []
