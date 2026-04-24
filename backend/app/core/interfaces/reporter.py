from abc import ABC, abstractmethod
from typing import Dict, Any

class IFeishuReporter(ABC):
    """
    🐦 飞书神经末梢接口
    定义了系统如何向用户反馈逻辑结论和进化过程。
    """
    @abstractmethod
    async def report_verdict(self, verdict: Dict[str, Any], chat_id: str) -> bool:
        """报告质证判决书（通常发送互动卡片）"""
        pass

    @abstractmethod
    async def sync_asset(self, verdict: Dict[str, Any], evolution_logs: Dict[str, Any]) -> bool:
        """将审计资产与进化日志同步到多维表格"""
        pass
