from abc import ABC, abstractmethod
from typing import Dict, Any, List

class IAgenticMemory(ABC):
    """
    🧠 自生长记忆主权接口
    定义了知识库如何将静态切片转化为动态记忆，并进行逻辑链接与进化。
    """
    @abstractmethod
    async def ingest_memory(self, chunk_data: Dict[str, Any]) -> str:
        """将逻辑切片转化为记忆节点"""
        pass

    @abstractmethod
    async def evolve_network(self, node_id: str) -> List[Dict[str, Any]]:
        """触发进化机制，寻找与现有知识库的支撑或冲突关系"""
        pass

    @abstractmethod
    async def query_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """在记忆库中搜索相关逻辑片段"""
        pass
