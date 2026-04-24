from abc import ABC, abstractmethod
from typing import List, Dict, Any
from uuid import UUID

class ISpineAuditor(ABC):
    """
    🛡️ 逻辑解构主权接口
    定义了 SpineDoc 核心引擎如何对文档进行物理切片和逻辑质证。
    """
    @abstractmethod
    async def extract_logic_spine(self, file_path: str) -> List[Dict[str, Any]]:
        """将文档解析为带指纹的逻辑切片 (Chunks)"""
        pass

    @abstractmethod
    async def cross_examine(self, query: str, doc_id: str) -> Dict[str, Any]:
        """执行联邦法庭质证，产出带有置信度的判决书 (Verdict)"""
        pass
