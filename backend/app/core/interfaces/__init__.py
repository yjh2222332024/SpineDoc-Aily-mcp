"""
SpineDoc Interfaces Facade
"""
from .auditor import ISpineAuditor
from .memory import IAgenticMemory
from .reporter import IFeishuReporter
from .storage import IDocumentStore

# Legacy Aliases
SpineReporter = IFeishuReporter

# 默认空实现 (Null Objects)
from typing import Dict, Any, List

class NullReporter(IFeishuReporter):
    async def report_result(self, result: Dict[str, Any], chat_id: str) -> bool: return True
    async def sync_asset(self, result: Dict[str, Any], evolution_logs: Dict[str, Any]) -> bool: return True

class NullMemory(IAgenticMemory):
    async def ingest_memory(self, chunk_data: Dict[str, Any]) -> str: return ""
    async def evolve_network(self, node_id: str) -> List[Dict[str, Any]]: return []
