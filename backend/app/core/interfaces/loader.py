from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any

class IDocumentLoader(ABC):
    """
     文档加载器接口
    负责将各种物理格式转化为 SpineDoc 核心理解的结构化文本。
    """
    @abstractmethod
    def can_handle(self, file_path: str) -> bool:
        """检查是否支持该文件格式"""
        pass

    @abstractmethod
    async def load(self, file_path: str) -> str:
        """加载文件并返回标准的 Markdown 字符串"""
        pass
