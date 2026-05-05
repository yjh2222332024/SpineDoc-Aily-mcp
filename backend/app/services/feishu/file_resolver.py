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

class FileResolver:
    def __init__(self, temp_dir: str = "backend/temp_uploads/"):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.cli_client = LarkCliClient()

    async def resolve(self, identifier: str) -> str:
        """
        解析标识符。
        1. 如果是 URL，直接返回。
        2. 如果符合 Feishu Token 模式，调用 CLI 下载。
        3. 否则视为本地路径。
        """
        # 1. URL 判定
        if identifier.startswith("http"):
            return identifier

        # 2. Feishu Token 判定 (box..., file..., doc...)
        # Aily 上传通常返回 boxcn...
        is_token = (
            identifier.startswith("box") or 
            identifier.startswith("file_") or 
            identifier.startswith("doc")
        )
        
        if is_token and len(identifier) > 10:
            logger.info(f"🚚 [Resolver] 检测到飞书 Token: {identifier[:10]}... 正在下载...")
            # 构造临时文件名，保留 token 作为名称
            temp_path = self.temp_dir / f"aily_{identifier}.pdf"
            
            success = await self.cli_client.download_drive_file(identifier, str(temp_path))
            if success and temp_path.exists():
                logger.info(f"✅ [Resolver] 下载成功: {temp_path}")
                return str(temp_path.absolute())
            else:
                logger.error(f"❌ [Resolver] 下载失败，回退到原始标识符")
                return identifier

        # 3. 默认视为本地路径
        return identifier
