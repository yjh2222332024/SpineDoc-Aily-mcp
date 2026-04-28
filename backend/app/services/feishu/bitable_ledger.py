import httpx
import json
import logging
import hashlib
import os
import re
import asyncio
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from backend.app.core.interfaces.storage import IDocumentStore

logger = logging.getLogger(__name__)

class BitableLedger(IDocumentStore):
    def __init__(self):
        from dotenv import load_dotenv
        load_dotenv(override=True)
        
        self.app_id = (os.getenv("FEISHU_APP_ID") or settings.FEISHU_APP_ID).strip()
        self.app_secret = (os.getenv("FEISHU_APP_SECRET") or settings.FEISHU_APP_SECRET).strip()
        
        self.wiki_node_id = "O3WDwZtqGiVETqkdFghcH78vnLd" 
        self.tables = {
            "docs": os.getenv("FEISHU_BITABLE_TABLE_ID") or "tbl1D9oIeervTl74",
            "chunks": os.getenv("FEISHU_BITABLE_CHUNK_TABLE_ID") or "tblgTgxUGTUykcU2",
            "toc": os.getenv("FEISHU_BITABLE_TOC_TABLE_ID") or "tbl3ee3QBlDOyqQE"
        }
        self._cached_obj_token = None
        self._doc_hash_map = {}

    async def get_token(self) -> str:
        env_proxies = ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"]
        for p in env_proxies: os.environ.pop(p, None)

        async with httpx.AsyncClient(trust_env=False, timeout=20.0) as client:
            resp = await client.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", 
                                   json={"app_id": self.app_id, "app_secret": self.app_secret})
            data = resp.json()
            if "tenant_access_token" not in data:
                raise Exception(f"Auth Failed: {data}")
            return data["tenant_access_token"]

    async def get_obj_token(self) -> str:
        if self._cached_obj_token: return self._cached_obj_token
        token = await self.get_token()
        async with httpx.AsyncClient(trust_env=False, timeout=20.0) as client:
            headers = {"Authorization": f"Bearer {token}"}
            wiki_url = f"https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node?token={self.wiki_node_id}"
            resp = await client.get(wiki_url, headers=headers)
            data = resp.json()
            if data.get("code") != 0:
                self._cached_obj_token = self.wiki_node_id 
                return self._cached_obj_token
            self._cached_obj_token = data["data"]["node"]["obj_token"]
            return self._cached_obj_token

    async def _api_request(self, method: str, url: str, json_data: Dict = None, params: Dict = None) -> Dict:
        token = await self.get_token()
        async with httpx.AsyncClient(trust_env=False, timeout=20.0) as client:
            headers = {"Authorization": f"Bearer {token}"}
            resp = await client.request(method, url, json=json_data, params=params, headers=headers)
            return resp.json()

    async def find_document_by_hash(self, file_hash: str) -> Optional[str]:
        """🚀 [V85.0] 确权查询：改用 POST /search 接口，彻底解决 InvalidFilter 问题"""
        obj_token = await self.get_obj_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{obj_token}/tables/{self.tables['docs']}/records/search"
        
        payload = {
            "filter": {
                "conjunction": "and",
                "conditions": [
                    {
                        "field_name": "文件哈希",
                        "operator": "is",
                        "value": [file_hash]
                    }
                ]
            }
        }
        
        resp = await self._api_request("POST", url, json_data=payload)
        items = resp.get("data", {}).get("items", [])
        return items[0].get("record_id") if items else None

    async def get_or_create_document(self, filename: str, file_hash: str, total_pages: int, force: bool = False) -> str:
        if not force:
            existing_id = await self.find_document_by_hash(file_hash)
            if existing_id: 
                self._doc_hash_map[existing_id] = file_hash
                return existing_id
        
        obj_token = await self.get_obj_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{obj_token}/tables/{self.tables['docs']}/records"
        fields = {"文件名": filename, "文件哈希": file_hash, "总页数": total_pages, "处理状态": "PROCESSING"}
        resp = await self._api_request("POST", url, {"fields": fields})
        rec_id = resp.get("data", {}).get("record", {}).get("record_id")
        if not rec_id:
            logger.error(f"❌ [Bitable] 创建文档记录失败: {resp}")
            raise Exception("Failed to create document record")
        self._doc_hash_map[rec_id] = file_hash
        return rec_id

    def _generate_coordinate(self, doc_rec_id: str, path: str, page: int) -> str:
        doc_hash = self._doc_hash_map.get(doc_rec_id, "unknown")
        return f"{doc_hash[:8]} :: {path} :: P{page}"

    async def save_chunks_batch(self, doc_rec_id: str, chunks: List[Dict[str, Any]]):
        obj_token = await self.get_obj_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{obj_token}/tables/{self.tables['chunks']}/records/batch_create"
        
        for i in range(0, len(chunks), 100):
            batch = chunks[i:i+100]
            records = []
            for c in batch:
                content = c.get("content", "")
                breadcrumb = c.get("breadcrumb", "")
                page = c.get("page_number", 0)
                records.append({
                    "fields": {
                        "文档关联": doc_rec_id, 
                        "正文内容": content,
                        "物理页码": page,
                        "逻辑面包屑": breadcrumb,
                        "逻辑指纹": hashlib.md5(content.encode()).hexdigest(),
                        "逻辑坐标": self._generate_coordinate(doc_rec_id, breadcrumb, page),
                        "Git版本": "v2.0-cloud"
                    }
                })
            resp = await self._api_request("POST", url, {"records": records})
            if resp.get("code") != 0:
                logger.error(f"❌ [Bitable] 批量写入分片失败: {resp}")
            else:
                print(f"📦 [Bitable] 已批量同步 {len(records)} 个分片。")

    async def save_toc_items_batch(self, doc_rec_id: str, toc_items: List[Dict[str, Any]]):
        obj_token = await self.get_obj_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{obj_token}/tables/{self.tables['toc']}/records/batch_create"
        
        for i in range(0, len(toc_items), 100):
            batch = toc_items[i:i+100]
            records = []
            for item in batch:
                title = item.get("title")
                page = item.get("logical_page", 0)
                records.append({
                    "fields": {
                        "文档关联": doc_rec_id, 
                        "标题": title,
                        "逻辑页码": page,
                        "逻辑坐标": self._generate_coordinate(doc_rec_id, title, page)
                    }
                })
            await self._api_request("POST", url, {"records": records})
            print(f"📡 [Bitable] 已批量同步 {len(records)} 个 TOC 条目。")

    async def wait_for_tags(self, doc_rec_id: str, timeout: int = 300) -> List[Dict[str, Any]]:
        """
        🚀 [V85.0] 语义反哺：改用 POST /search 接口进行健壮轮询。
        """
        import asyncio
        import re
        obj_token = await self.get_obj_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{obj_token}/tables/{self.tables['chunks']}/records/search"
        
        # 🏛️ 专业的 JSON 过滤器，完全避开 URL 编码地狱
        payload = {
            "filter": {
                "conjunction": "and",
                "conditions": [
                    {
                        "field_name": "文档关联",
                        "operator": "is",
                        "value": [doc_rec_id]
                    }
                ]
            }
        }
        
        start_time = asyncio.get_event_loop().time()
        print(f"⏳ [Bitable] 启动语义反哺轮询 (Target Doc: {doc_rec_id})...")
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            # 🏛️ 发送 POST 搜索请求
            resp = await self._api_request("POST", url, json_data=payload)
            if resp.get("code") != 0:
                logger.error(f"❌ [Bitable] 搜索请求失败: {resp.get('msg')}")
                await asyncio.sleep(10)
                continue

            items = resp.get("data", {}).get("items", [])
            
            if not items:
                elapsed = asyncio.get_event_loop().time() - start_time
                print(f"📡 [Watcher] 正在同步云端索引 (已耗时 {int(elapsed)}s)...")
                await asyncio.sleep(10)
                continue
                
            tagged_items = [it for it in items if it.get("fields", {}).get("语义标签")]
            tagged_count = len(tagged_items)
            
            print(f"📡 [Watcher] 云端打标进度: {tagged_count}/{len(items)} 个分片...")
            
            if tagged_count >= len(items) and len(items) > 0:
                print(f"✅ [Bitable] 云端语义反哺就绪！")
                results = []
                for it in items:
                    fields = it.get("fields", {})
                    # 🏛️ 鲁棒性修正：确保 coord 是字符串
                    coord = fields.get("逻辑坐标", "")
                    if isinstance(coord, list) and coord: coord = str(coord[0])
                    elif not isinstance(coord, str): coord = str(coord)
                    
                    page_match = re.search(r'P(\d+)', coord)
                    page_num = int(page_match.group(1)) if page_match else 0
                    
                    # 🏛️ 鲁棒性修正：确保标签格式统一
                    raw_tags = fields.get("语义标签", [])
                    if isinstance(raw_tags, str): logic_tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
                    else: logic_tags = raw_tags
                    
                    # 🏛️ 鲁棒性修正：确保 content 是字符串
                    content = fields.get("正文内容", "")
                    if isinstance(content, list) and content: content = str(content[0])
                    elif not isinstance(content, str): content = str(content)
                    
                    # 🏛️ 鲁棒性修正：确保 breadcrumb 是字符串
                    breadcrumb = fields.get("逻辑面包屑", "")
                    if isinstance(breadcrumb, list) and breadcrumb: breadcrumb = str(breadcrumb[0])
                    elif not isinstance(breadcrumb, str): breadcrumb = str(breadcrumb)
                    
                    results.append({
                        "id": it.get("record_id"),
                        "content": content,
                        "logic_tags": logic_tags,
                        "page_number": page_num,
                        "breadcrumb": breadcrumb
                    })
                return results
                
            await asyncio.sleep(10)
            
        raise TimeoutError(f"❌ [Bitable] 云端打标轮询超时。")

    async def search_chunks(self, query: str, doc_record_id: Optional[str] = None, tags: List[str] = None, limit: int = 20) -> List[Dict]:
        """
        🚀 [V85.0] 精准召回：利用 Bitable POST /search 进行标签与全文混合检索
        """
        obj_token = await self.get_obj_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{obj_token}/tables/{self.tables['chunks']}/records/search"
        
        conditions = []
        if doc_record_id:
            conditions.append({"field_name": "文档关联", "operator": "is", "value": [doc_record_id]})
        
        # 🏛️ 标签碰撞逻辑：如果传入了关键词标签
        if tags:
            tag_conditions = []
            for t in tags[:5]: # 取前 5 个核心标签
                tag_conditions.append({"field_name": "语义标签", "operator": "contains", "value": [t]})
            if tag_conditions:
                conditions.append({"conjunction": "or", "conditions": tag_conditions})

        payload = {
            "filter": {"conjunction": "and", "conditions": conditions} if conditions else None,
            "automatic_fields": True,
            "page_size": limit
        }
        
        resp = await self._api_request("POST", url, json_data=payload)
        items = resp.get("data", {}).get("items", [])
        
        results = []
        for it in items:
            f = it.get("fields", {})
            results.append({
                "id": it.get("record_id"),
                "content": f.get("正文内容", ""),
                "breadcrumb": f.get("逻辑面包屑", ""),
                "page_number": f.get("物理页码", 0),
                "logic_tags": f.get("语义标签", [])
            })
        return results

bitable_ledger = BitableLedger()

