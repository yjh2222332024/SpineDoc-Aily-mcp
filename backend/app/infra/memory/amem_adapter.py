"""
A-mem Adapter - Agentic Memory 适配器
========================================
职责：将 A-mem 项目的 AgenticMemorySystem 集成到 SpineDoc 中。
原则：封装底层实现，通过 IAgenticMemory 接口与核心引擎通信。
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# 确保能导入 A-mem
project_root = Path(__file__).resolve().parent.parent.parent.parent
amem_path = project_root / "A-mem"
if str(amem_path) not in sys.path:
    sys.path.insert(0, str(amem_path))

from backend.app.core.interfaces import IAgenticMemory
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class AmemAdapter(IAgenticMemory):
    def __init__(self, memory_table_id: Optional[str] = None):
        try:
            from agentic_memory.cloud_retriever import CloudRetriever
            from agentic_memory.memory_system import AgenticMemorySystem
            from agentic_memory.llm_controller import LLMController

            table_id = (
                memory_table_id
                or os.getenv("FEISHU_BITABLE_MEMORY_TABLE_ID")
                or os.getenv("FEISHU_BITABLE_CHUNK_TABLE_ID", "")
            )
            if not table_id:
                logger.warning(
                    "⚠️ [AmemAdapter] FEISHU_BITABLE_MEMORY_TABLE_ID not set, "
                    "A-MEM will use in-memory retriever (no persistence)."
                )
                self.system = None
                return

            retriever = CloudRetriever(table_id=table_id)
            llm_ctrl = LLMController(
                backend="openai",
                model=settings.REAL_LLM_MODEL,
                api_key=settings.LLM_API_KEY,
            )
            self.system = AgenticMemorySystem(
                retriever=retriever,
                llm_controller=llm_ctrl,
            )
            logger.info("[AmemAdapter] Agentic Memory system initialized.")
        except Exception as e:
            logger.error(f"[AmemAdapter] Initialization failed: {e}")
            self.system = None

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
