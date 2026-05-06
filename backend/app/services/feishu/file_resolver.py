"""
🧬 File Resolver - 多源文件解析适配器
========================================
职责：将 Aily 的 file_token 或各种路径解析为后端引擎可处理的本地路径。
"""
import os
import logging
from pathlib import Path
from backend.app.infra.lark_cli_client import LarkCliClient

logger = logging.getLogger(__name__)

from typing import List
from backend.app.core.interfaces.cloud_adapter import ICloudDocumentAdapter
from .feishu_cloud_adapter import FeishuCloudAdapter

class FileResolver:
    """
    🧬 File Resolver - 多源文件解析适配器 (Uncle Bob 版)
    ========================================
    职责：协调各个 CloudAdapter 解决文件解析问题。
    """
    def __init__(self, 
                 temp_dir: str = "backend/temp_uploads/",
                 adapters: List[ICloudDocumentAdapter] = None):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        # 默认注入 FeishuAdapter，体现 OCP 原则
        self.adapters = adapters or [FeishuCloudAdapter()]

    async def resolve(self, identifier: str) -> str:
        """
        解析标识符。
        1. URL 判定。
        2. 询问适配器是否能处理。
        3. 否则视为本地路径。
        """
        if identifier.startswith("http"):
            return identifier

        for adapter in self.adapters:
            if adapter.can_handle(identifier):
                temp_path = self.temp_dir / f"resolved_{identifier}.pdf"
                success = await adapter.download(identifier, str(temp_path))
                if success and temp_path.exists():
                    return str(temp_path.absolute())

        # 默认视为本地路径
        return identifier
