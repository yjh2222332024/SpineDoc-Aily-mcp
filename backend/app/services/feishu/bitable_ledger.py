import httpx
import json
import logging
import hashlib
import os
import re
import asyncio
from typing import List, Dict, Any, Optional, Union
from backend.app.core.config import settings
from backend.app.core.interfaces.storage import IDocumentStore

logger = logging.getLogger(__name__)

class BitableLedger(IDocumentStore):
    """
    BitableLedger: Professional cloud ledger.
    Unified formatting and robust record handling.
    """
    def __init__(self):
        # 🛡️ 架构师纪律：配置必须确权
        self.app_id = (os.getenv("FEISHU_APP_ID") or settings.FEISHU_APP_ID).strip()
        self.app_secret = (os.getenv("FEISHU_APP_SECRET") or settings.FEISHU_APP_SECRET).strip()
        self.wiki_node_id = "O3WDwZtqGiVETqkdFghcH78vnLd" 
        
        self.tables = {
            "docs": os.getenv("FEISHU_BITABLE_TABLE_ID") or "tbl1D9oIeervTl74",
            "chunks": os.getenv("FEISHU_BITABLE_CHUNK_TABLE_ID") or "tblgTgxUGTUykcU2",
            "toc": os.getenv("FEISHU_BITABLE_TOC_TABLE_ID") or "tbl3ee3QBlDOyqQE"
        }
        self._cached_obj_token = None

    async def _get_token(self) -> str:
        url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
        payload = {"app_id": self.app_id, "app_secret": self.app_secret}
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, json=payload)
            return resp.json().get("tenant_access_token")

    async def _get_app_token(self) -> str:
        if self._cached_obj_token: return self._cached_obj_token
        token = await self._get_token()
        url = f"https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node?token={self.wiki_node_id}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            data = resp.json()
            self._cached_obj_token = data.get("data", {}).get("node", {}).get("obj_token") or self.wiki_node_id
            return self._cached_obj_token

    async def _api_request(self, method: str, url: str, json_data: Dict = None) -> Dict:
        token = await self._get_token()
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.request(method, url, json=json_data, headers=headers)
            return resp.json()

    def _extract_record_id(self, field_value: Any) -> Optional[str]:
        if not field_value: return None
        if isinstance(field_value, list) and field_value:
            item = field_value[0]
            return item.get("id") if isinstance(item, dict) else str(item)
        return str(field_value)

    async def update_document_status(self, doc_rec_id: str, status: str):
        app_token = await self._get_app_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{self.tables['docs']}/records/{doc_rec_id}"
        await self._api_request("PUT", url, {"fields": {"处理状态": status}})
        print(f"📊 [Status] {doc_rec_id[:8]} -> {status}")

    async def get_or_create_document(self, filename: str, file_hash: str, total_pages: int, force: bool = False) -> str:
        # 简化版实现，优先满足流程通畅
        app_token = await self._get_app_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{self.tables['docs']}/records"
        fields = {"文件名": filename, "文件哈希": file_hash, "总页数": total_pages, "处理状态": "PROCESSING"}
        resp = await self._api_request("POST", url, {"fields": fields})
        return resp.get("data", {}).get("record", {}).get("record_id")

    async def save_chunks_batch(self, doc_rec_id: str, chunks: List[Dict[str, Any]]):
        app_token = await self._get_app_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{self.tables['chunks']}/records/batch_create"
        records = []
        for c in chunks:
            records.append({"fields": {
                "文档关联": [doc_rec_id],
                "正文内容": c.get("content", ""),
                "物理页码": c.get("page_number", 0),
                "逻辑面包屑": c.get("breadcrumb", ""),
                "逻辑指纹": hashlib.md5(c.get("content", "").encode()).hexdigest(),
                "Git版本": "v2.0-cloud"
            }})
        await self._api_request("POST", url, {"records": records})

    async def save_toc_items_batch(self, doc_rec_id: str, toc_items: List[Dict[str, Any]]):
        app_token = await self._get_app_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{self.tables['toc']}/records/batch_create"
        records = [{"fields": {"文档关联": [doc_rec_id], "标题": it.get("title"), "逻辑页码": it.get("logical_page", 0)}} for it in toc_items]
        await self._api_request("POST", url, {"records": records})

    async def wait_for_tags(self, doc_rec_id: str, timeout: int = 300) -> List[Dict[str, Any]]:
        app_token = await self._get_app_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{self.tables['chunks']}/records/search"
        payload = {"filter": {"conjunction": "and", "conditions": [{"field_name": "文档关联", "operator": "is", "value": [doc_rec_id]}]}}
        
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            resp = await self._api_request("POST", url, json_data=payload)
            items = resp.get("data", {}).get("items", [])
            tagged_items = [it for it in items if it.get("fields", {}).get("语义标签")]
            
            if tagged_items and len(tagged_items) >= len(items):
                results = []
                for it in items:
                    f = it.get("fields", {})
                    # 🚀 [V100.0] 核心补完：必须回填 summary 和 doc_record_id
                    results.append({
                        "id": it.get("record_id"),
                        "doc_record_id": doc_rec_id,
                        "content": f.get("正文内容", ""),
                        "summary": f.get("逻辑摘要", f.get("AI摘要", "")),
                        "logic_tags": f.get("语义标签", []),
                        "embedding": json.loads(f.get("向量表征", "null")) if f.get("向量表征") else None
                    })
                return results
            await asyncio.sleep(5)
        return []

    async def fetch_chunks_by_galaxy(self, galaxy_rec_id: str) -> List[Dict]:
        app_token = await self._get_app_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{self.tables['chunks']}/records/search"
        payload = {"filter": {"conjunction": "and", "conditions": [{"field_name": "星系关联", "operator": "contains", "value": [galaxy_rec_id]}]}}
        resp = await self._api_request("POST", url, json_data=payload)
        items = resp.get("data", {}).get("items", [])
        return [{
            "id": it["record_id"],
            "doc_record_id": self._extract_record_id(it["fields"].get("文档关联")),
            "summary": it["fields"].get("逻辑摘要", ""),
            "content": it["fields"].get("正文内容", "")
        } for it in items]

bitable_ledger = BitableLedger()
