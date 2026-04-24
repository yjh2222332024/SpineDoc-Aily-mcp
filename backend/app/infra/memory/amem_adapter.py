
"""
🧠 A-mem Adapter - Agentic Memory 适配器
========================================
职责：将 A-mem 项目的 AgenticMemorySystem 集成到 SpineDoc 中。
原则：封装底层实现，通过 IAgenticMemory 接口与核心引擎通信。
"""

import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

# 确保能导入 A-mem
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
amem_path = project_root / "A-mem"
if str(amem_path) not in sys.path:
    sys.path.insert(0, str(amem_path))

from backend.app.core.interfaces import IAgenticMemory
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class AmemAdapter(IAgenticMemory):
    def __init__(self):
        try:
            from agentic_memory.memory_system import AgenticMemorySystem
            
            # 初始化 A-mem 系统
            # 注意：A-mem 目前强依赖 OpenAI 格式，我们尝试通过环境变量注入豆包
            # 如果 A-mem 源码不支持 base_url，我们可能需要对其进行手术式修复
            self.system = AgenticMemorySystem(
                model_name='all-MiniLM-L6-v2', # 使用本地轻量嵌入
                llm_backend="openai",
                llm_model=settings.LLM_MODEL_NAME,
                api_key=settings.LLM_API_KEY
            )
            logger.info("🧠 [AmemAdapter] Agentic Memory 系统初始化成功")
        except Exception as e:
            logger.error(f"❌ [AmemAdapter] 初始化失败: {e}")
            self.system = None

    async def ingest_memory(self, chunk_data: Dict[str, Any]) -> str:
        """将 SpineDoc 的 Chunk 转化为 A-mem Note"""
        if not self.system: return ""
        
        content = chunk_data.get("content", "")
        # 映射元数据
        metadata = {
            "category": "AuditChunk",
            "tags": chunk_data.get("logic_tags", []),
            "doc_id": str(chunk_data.get("document_id", ""))
        }
        
        try:
            # A-mem 的 add_note 是同步的，我们在这里封装
            note_id = self.system.add_note(content, **metadata)
            return note_id
        except Exception as e:
            logger.error(f"❌ [AmemAdapter] 记忆摄入失败: {e}")
            return ""

    async def evolve_network(self, node_id: str) -> List[Dict[str, Any]]:
        """
        触发进化分析并提取逻辑连接。
        返回格式：[{"target_id": "...", "type": "support|contradict", "reason": "..."}]
        """
        if not self.system: return []
        
        try:
            # 在 A-mem 中，进化通常在 add_note 时自动触发
            note = self.system.read(node_id)
            if not note: return []
            
            logic_connections = []
            for link in note.links:
                if isinstance(link, dict):
                    # 🚀 [V52.6] 提取带类型的进化逻辑
                    logic_connections.append({
                        "target_id": link.get("id"),
                        "type": link.get("type", "support"),
                        "reason": link.get("reason", "语义关联")
                    })
                else:
                    # 兼容旧版简单字符串链接
                    logic_connections.append({
                        "target_id": str(link),
                        "type": "support",
                        "reason": "语义关联"
                    })
            
            return logic_connections
        except Exception as e:
            logger.error(f"❌ [AmemAdapter] 逻辑进化分析失败: {e}")
            return []
