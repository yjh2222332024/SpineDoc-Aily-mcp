"""
A-mem Adapter - Agentic Memory 适配器
========================================
职责：将 A-mem 项目的 AgenticMemorySystem 集成到 SpineDoc 中。
原则：封装底层实现，通过 IAgenticMemory 接口与核心引擎通信。
"""

import logging
from typing import Dict, Any, List, Optional

from backend.app.core.interfaces import IAgenticMemory
from backend.app.core.config import settings
from .vendor.agentic_memory.cloud_retriever import CloudRetriever
from .vendor.agentic_memory.memory_system import AgenticMemorySystem
from .vendor.agentic_memory.llm_controller import LLMController

logger = logging.getLogger(__name__)


class AmemAdapter(IAgenticMemory):
    def __init__(self, memory_table_id: Optional[str] = None):
        table_id = (
            memory_table_id
            or settings.FEISHU_BITABLE_MEMORY_TABLE_ID
            or settings.FEISHU_BITABLE_CHUNK_TABLE_ID
        )
        if not table_id:
            logger.error(
                " [AmemAdapter] FEISHU_BITABLE_MEMORY_TABLE_ID 未配置。"
                "A-MEM 将使用内存模式，重启后记忆丢失。"
                "请在 .env 中设置 FEISHU_BITABLE_MEMORY_TABLE_ID"
            )
            raise EnvironmentError(
                "FEISHU_BITABLE_MEMORY_TABLE_ID 未配置。"
                "请在 .env 中设置 FEISHU_BITABLE_MEMORY_TABLE_ID"
            )

        self.system = AgenticMemorySystem(
            retriever=CloudRetriever(table_id=table_id),
            llm_controller=LLMController(
                backend="openai",
                model=settings.REAL_LLM_MODEL,
                api_key=settings.LLM_API_KEY,
            ),
        )
        logger.info("[AmemAdapter] Agentic Memory system initialized.")

    async def ingest_memory(self, chunk_data: Dict[str, Any]) -> str:
        """将 SpineDoc 的 Chunk 转化为 A-mem Note"""
        if not self.system:
            return ""

        content = chunk_data.get("content", "")
        metadata = {
            "category": "AuditChunk",
            "tags": chunk_data.get("logic_tags", []),
            "doc_id": str(chunk_data.get("document_id", "")),
        }

        try:
            note_id = await self.system.add_note(content, **metadata)
            return note_id
        except Exception as e:
            logger.error(f"[AmemAdapter] Memory ingest failed: {e}")
            return ""

    async def evolve_network(self, node_id: str) -> List[Dict[str, Any]]:
        """
        Trigger evolution analysis and extract logical connections.
        Returns: [{"target_id": "...", "type": "support|contradict", "reason": "..."}]
        """
        if not self.system:
            return []

        try:
            note = self.system.read(node_id)
            if not note:
                return []

            logic_connections = []
            for link in note.links:
                if isinstance(link, dict):
                    logic_connections.append({
                        "target_id": link.get("id"),
                        "type": link.get("type", "support"),
                        "reason": link.get("reason", "semantic link"),
                    })
                else:
                    logic_connections.append({
                        "target_id": str(link),
                        "type": "support",
                        "reason": "semantic link",
                    })

            return logic_connections
        except Exception as e:
            logger.error(f"[AmemAdapter] Evolution analysis failed: {e}")
            return []

    async def query_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """在 A-MEM 中执行语义搜索"""
        if not self.system:
            return []
        
        try:
            # 使用 AgenticMemorySystem 的 search_agentic 方法
            mem_results = await self.system.search_agentic(query, k=limit)
            
            # 规范化结果
            normalized = []
            for r in mem_results:
                normalized.append({
                    "id": r.get("id"),
                    "content": r.get("content", ""),
                    "logic_tags": r.get("tags", []),
                    "confidence": r.get("score", 0.75),
                    "document_id": r.get("doc_id", "A-MEM"),
                    "origin": "A-MEMORY"
                })
            return normalized
        except Exception as e:
            logger.error(f"[AmemAdapter] Memory query failed: {e}")
            return []
