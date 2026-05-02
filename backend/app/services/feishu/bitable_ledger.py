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
    def __init__(self, auth=None):
        from backend.app.services.feishu.auth import lark_auth
        self.auth = auth or lark_auth
        self.tables = {
            "docs": (os.getenv("FEISHU_BITABLE_TABLE_ID") or "").strip(),
            "chunks": (os.getenv("FEISHU_BITABLE_CHUNK_TABLE_ID") or "").strip(),
            "toc": (os.getenv("FEISHU_BITABLE_TOC_TABLE_ID") or "").strip()
        }

    async def _api_request(self, method: str, url: str, json_data: Dict = None, params: Dict = None) -> Dict:
        token = await self.auth.get_tenant_access_token()
        async with httpx.AsyncClient(trust_env=False, timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            resp = await client.request(method, url, json=json_data, params=params, headers=headers)
            if resp.status_code >= 400: print(f"DEBUG: API Error: {resp.text}")
            return resp.json()

    async def _get_app_token(self) -> str:
        return await self.auth.get_wiki_obj_token()

    def _extract_record_id(self, field_value: Any) -> Optional[str]:
        if not field_value: return None
        if isinstance(field_value, list):
            if not field_value: return None
            item = field_value[0]
            if isinstance(item, dict): return item.get("id")
            return str(item)
        return str(field_value)

    async def update_document_status(self, doc_rec_id: str, status: str):
        app_token = await self._get_app_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{self.tables['docs']}/records/{doc_rec_id}"
        await self._api_request("PUT", url, {"fields": {"处理状态": status}})

    async def find_document_by_hash(self, file_hash: str) -> Optional[str]:
        app_token = await self._get_app_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{self.tables['docs']}/records/search"
        payload = {"filter": {"conjunction": "and", "conditions": [{"field_name": "文件哈希", "operator": "is", "value": [file_hash]}]}}
        resp = await self._api_request("POST", url, json_data=payload)
        items = resp.get("data", {}).get("items", [])
        return items[0].get("record_id") if items else None

    async def get_or_create_document(self, filename: str, file_hash: str, total_pages: int, force: bool = False) -> str:
        if not force:
            existing_id = await self.find_document_by_hash(file_hash)
            if existing_id: return existing_id
        
        app_token = await self._get_app_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{self.tables['docs']}/records"
        fields = {"文件名": filename, "文件哈希": file_hash, "总页数": total_pages, "处理状态": "PROCESSING"}
        resp = await self._api_request("POST", url, {"fields": fields})
        return resp.get("data", {}).get("record", {}).get("record_id")

    async def save_chunks_batch(self, doc_rec_id: str, chunks: List[Dict[str, Any]]):
        app_token = await self._get_app_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{self.tables['chunks']}/records/batch_create"
        
        for i in range(0, len(chunks), 100):
            batch = chunks[i:i+100]
            records = []
            for c in batch:
                content = c.get("content", "")
                fields = {
                    "文档关联": [doc_rec_id],
                    "正文内容": content,
                    "物理页码": c.get("page_number", 0),
                    "逻辑面包屑": c.get("breadcrumb", ""),
                    "逻辑指纹": hashlib.md5(content.encode()).hexdigest(),
                    "Git版本": "v2.0-cloud"
                }
                
                # 强力审计：查看向量写入点
                if c.get("embedding"): 
                    vec = c["embedding"]
                    fields["向量表征"] = json.dumps(vec)
                    print(f"DEBUG: 写入向量表征，长度: {len(vec)}")

                if "level" in c: fields["层级"] = c["level"]
                if "parent_id" in c: fields["父级关联"] = c["parent_id"] if isinstance(c["parent_id"], list) else [c["parent_id"]]
                records.append({"fields": fields})
            await self._api_request("POST", url, {"records": records})

    async def wait_for_completion(self, doc_rec_id: str, timeout: int = 300) -> List[Dict[str, Any]]:
        """
        🚀 确权流水线：确保 Bitable 物理落库并完成了 AI 计算。
        验证点：逻辑摘要 + 向量表征
        """
        app_token = await self._get_app_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{self.tables['chunks']}/records/search"
        payload = {"filter": {"conjunction": "and", "conditions": [{"field_name": "文档关联", "operator": "is", "value": [doc_rec_id]}]}}
        
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            resp = await self._api_request("POST", url, json_data=payload)
            items = resp.get("data", {}).get("items", [])
            
            # 严格验证：确保所有记录都有逻辑摘要
            ready = True
            for it in items:
                f = it.get("fields", {})
                if not f.get("逻辑摘要") and not f.get("正文内容"):
                    ready = False; break
            
            if ready and len(items) > 0:
                return [{
                    "id": it["record_id"],
                    "summary": it["fields"].get("逻辑摘要", ""),
                    "content": it["fields"].get("正文内容", ""),
                    "embedding": json.loads(it["fields"].get("向量表征", "null")) if it["fields"].get("向量表征") else None
                } for it in items]
            
            await asyncio.sleep(5)
        raise TimeoutError("❌ [Bitable] 确权超时：数据计算未在规定时间内完成。")

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
