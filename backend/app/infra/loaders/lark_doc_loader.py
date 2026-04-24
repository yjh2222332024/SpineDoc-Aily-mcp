import asyncio
import json
import subprocess
from pathlib import Path
from backend.app.core.interfaces.loader import IDocumentLoader

class LarkDocLoader(IDocumentLoader):
    def __init__(self, cli_path: str = "bin/lark-cli.exe"):
        self.cli_path = str(Path(cli_path).absolute())

    def can_handle(self, file_path: str) -> bool:
        # 识别飞书文档 URL 或特定的 doc_id 前缀
        return "feishu.cn/docx/" in file_path or file_path.startswith("doc")

    async def load(self, file_path: str) -> str:
        """通过 lark-cli 将飞书文档导出为 Markdown"""
        # 这里利用 lark-cli doc +export 功能
        # 假设命令格式: lark-cli doc +export --doc-token XXX --type markdown
        token = self._extract_token(file_path)
        cmd = [self.cli_path, "doc", "+export", "--doc-token", token, "--type", "markdown"]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            # 返回导出的 Markdown 内容
            return stdout.decode()
        else:
            raise Exception(f"飞书文档导出失败: {stderr.decode()}")

    def _extract_token(self, url: str) -> str:
        # 从 URL 中提取 doc_token 的简单逻辑
        if "/" in url:
            return url.split("/")[-1].split("?")[0]
        return url
