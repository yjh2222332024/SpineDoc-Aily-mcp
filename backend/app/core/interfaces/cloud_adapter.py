from abc import ABC, abstractmethod
from typing import Optional

class ICloudDocumentAdapter(ABC):
    """
     [V280.0] 云文档适配器接口
    职责：将各种云端标识符（Token/URL）转换为本地可处理的物理文件。
    遵循：Uncle Bob 的 DIP (Dependency Inversion Principle)。
    """
    
    @abstractmethod
    async def download(self, identifier: str, target_path: str) -> bool:
        """下载云端文件到指定本地路径"""
        pass

    @abstractmethod
    def can_handle(self, identifier: str) -> bool:
        """判定该适配器是否能处理给定的标识符"""
        pass
