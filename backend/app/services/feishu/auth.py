"""
LarkAuth - Feishu authentication abstraction
Encapsulates token management for Bitable and Wiki APIs.
"""
import httpx
import os
from typing import Optional

class LarkAuth:
    def __init__(self):
        from backend.app.core.config import settings
        self.app_id = settings.FEISHU_APP_ID.strip()
        self.app_secret = settings.FEISHU_APP_SECRET.strip()
        self.wiki_node_id = settings.FEISHU_WIKI_NODE_ID.strip()
        self._tenant_token: Optional[str] = None
        self._obj_token: Optional[str] = None

    async def get_tenant_access_token(self) -> str:
        """Get tenant access token for API calls"""
        env_proxies = ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]
        for p in env_proxies:
            os.environ.pop(p, None)

        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": self.app_id, "app_secret": self.app_secret}
        async with httpx.AsyncClient(trust_env=False, timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            data = resp.json()
            if "tenant_access_token" not in data:
                raise Exception(f"Auth failed: {data}")
            self._tenant_token = data["tenant_access_token"]
            return self._tenant_token

    async def get_wiki_obj_token(self) -> str:
        """Get wiki object token for Bitable access"""
        if self._obj_token:
            return self._obj_token

        token = await self.get_tenant_access_token()
        url = f"https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node?token={self.wiki_node_id}"
        async with httpx.AsyncClient(trust_env=False, timeout=20.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            data = resp.json()
            if data.get("code") == 0:
                self._obj_token = data["data"]["node"]["obj_token"]
            else:
                # fallback: use node_id as obj_token
                self._obj_token = self.wiki_node_id
            return self._obj_token

lark_auth = LarkAuth()