import logging
from backend.app.core.interfaces.cloud_adapter import ICloudDocumentAdapter
from backend.app.infra.lark_cli_client import LarkCliClient

logger = logging.getLogger(__name__)

class FeishuCloudAdapter(ICloudDocumentAdapter):
    """
     [V280.1] 飞书云文档具体实现
    职责：封装飞书特有的 boxcn/file/doc 下载逻辑。
    """
    
    def __init__(self):
        self.cli_client = LarkCliClient()

    def can_handle(self, identifier: str) -> bool:
        """判定是否为飞书 Token"""
        return (
            identifier.startswith("box") or 
            identifier.startswith("file_") or 
            identifier.startswith("doc")
        ) and len(identifier) > 10

    async def download(self, identifier: str, target_path: str) -> bool:
        logger.info(f"🚚 [FeishuAdapter] 正在下载飞书资源: {identifier[:10]}...")
        return await self.cli_client.download_drive_file(identifier, target_path)
