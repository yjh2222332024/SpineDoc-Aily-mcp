import asyncio
import json
import httpx
import os
from pathlib import Path
from backend.app.core.config import settings
from backend.app.core.interfaces.loader import IDocumentLoader


async def _get_tenant_token() -> str:
    """换取飞书租户凭证"""
    manual_token = settings.FEISHU_AILY_TOKEN
    if manual_token:
        print(" [LarkLoader] 正在使用手动注入的黄金令牌...")
        return manual_token.strip()

    url = f"https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    auth_id = settings.FEISHU_APP_ID
    auth_secret = settings.FEISHU_APP_SECRET

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={
            "app_id": auth_id,
            "app_secret": auth_secret
        })
        return resp.json().get("tenant_access_token", "")


class LarkDocLoader(IDocumentLoader):
    def __init__(self, cli_path: str = "bin/lark-cli.exe"):
        self.cli_path = str(Path(cli_path).absolute())

    def can_handle(self, file_path: str) -> bool:
        #  [V112.0] 扩展判定：支持飞书文档 (docx) 和 知识库 (wiki) 链接
        return any(x in file_path for x in ["feishu.cn/docx/", "larksuite.com/docx/", "feishu.cn/wiki/", "larksuite.com/wiki/"])

    async def load(self, file_path: str) -> str:
        """通过 lark-cli 将飞书文档导出为 Markdown"""
        token = self._extract_token(file_path)

        #  [V111.0] 认证一公里：注入黄金令牌
        tenant_token = await _get_tenant_token()
        
        env = os.environ.copy()
        env["LARK_TENANT_ACCESS_TOKEN"] = tenant_token
        env["FEISHU_TENANT_ACCESS_TOKEN"] = tenant_token
        
        #  使用官方推荐的 +fetch 命令
        cmd = [
            self.cli_path, "docs", "+fetch", 
            "--api-version", "v2", 
            "--doc", token, 
            "--doc-format", "markdown"
        ]
        
        print(f" [LarkLoader] 正在利用黄金令牌捕获云端知识: {token[:8]}...")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            try:
                #  解析 JSON 响应
                resp_json = json.loads(stdout.decode())
                if not resp_json.get("ok"):
                    raise Exception(f"业务错误: {resp_json.get('msg', '未知错误')}")
                
                content = resp_json.get("data", {}).get("document", {}).get("content", "")
                return content
            except json.JSONDecodeError:
                # 兼容直接返回文本的情况
                return stdout.decode()
        else:
            raise Exception(f"飞书文档导出失败: {stderr.decode()}")

    def _extract_token(self, url: str) -> str:
        # 从 URL 中提取 doc_token 的简单逻辑
        if "/" in url:
            return url.split("/")[-1].split("?")[0]
        return url
