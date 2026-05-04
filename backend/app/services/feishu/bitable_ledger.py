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
    BitableLedger: Ground Truth Persistence (V4.1)
    =============================================
    职责：物理确权，确保每一个 API 调用都有确凿的物理座标。
    """
    def __init__(self, auth=None):
        from backend.app.services.feishu.auth import lark_auth
        self.auth = auth or lark_auth
        
        manifest_path = "backend/storage/bitable_schema_manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            self.manifest = json.load(f)
            
        self.tables = self.manifest["tables"]
        self.app_token = self.manifest["base_token"]

    @staticmethod
    def _plain_text(val) -> str:
        if isinstance(val, list):
            return ''.join(item.get('text', '') for item in val if isinstance(item, dict))
        return str(val) if val else ""

    async def _api_request(self, method: str, url: str, json_data: Dict = None, params: Dict = None) -> Dict:
        # 🛡️ 架构师守则：URL 必须是纯净的。现场打印最终物理座标。
        print(f"DEBUG_FINAL_URL: {url}") 
        token = await self.auth.get_tenant_access_token()
        async with httpx.AsyncClient(trust_env=False, timeout=30.0) as client:
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            resp = await client.request(method, url, json=json_data, params=params, headers=headers)
            data = resp.json()
            if data.get("code") != 0:
                logger.error(f"❌ [Bitable-API] Failed: {data.get('msg')} | URL: {url}")
            return data

    async def _get_app_token(self) -> str:
        return await self.auth.get_wiki_obj_token()

    def _extract_record_id(self, field_value: Any) -> List[str]:
        """
        🚀 [V155.0] 物理提取强化：全兼容 Bitable Link 字段
        """
        if not field_value: return []
        
        # 格式 A: {'link_record_ids': ['recxxx', ...]}
        if isinstance(field_value, dict) and "link_record_ids" in field_value:
            return [str(i) for i in field_value["link_record_ids"]]
            
        # 格式 B: [{'record_ids': ['recxxx', ...]}, ...] - 常见于反向关联
        if isinstance(field_value, list):
            res = []
            for item in field_value:
                if isinstance(item, dict):
                    if "record_ids" in item:
                        res.extend([str(i) for i in item["record_ids"]])
                    else:
                        res.append(str(item.get("id") or item.get("record_id", "")))
                else:
                    res.append(str(item))
            return [r for r in res if r]
            
        return [str(field_value)]

    async def find_document_by_hash(self, file_hash: str) -> Optional[str]:
        """🚀 [V85.0] 确权查询：改用 POST /search 接口，彻底解决 InvalidFilter 问题"""
        table_id = self.tables['documents']['id']
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/search"
        
        payload = {
            "filter": {
                "conjunction": "and",
                "conditions": [{"field_name": "文件哈希", "operator": "is", "value": [file_hash]}]
            }
        }
        
        resp = await self._api_request("POST", url, json_data=payload)
        items = resp.get("data", {}).get("items", [])
        return items[0].get("record_id") if items else None

    async def get_or_create_document(self, filename: str, file_hash: str, total_pages: int, force: bool = False) -> str:
        if not force:
            existing_id = await self.find_document_by_hash(file_hash)
            if existing_id: return existing_id
        
        # 🚀 物理确权：严禁重复 POST
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.tables['documents']['id']}/records"
        fields = {
            "文件名": filename,
            "文件哈希": file_hash,
            "总页数": total_pages,
            "处理状态": "PROCESSING"
        }
        resp = await self._api_request("POST", url, {"fields": fields})
        return resp.get("data", {}).get("record", {}).get("record_id")

    async def get_or_create_sovereign_root(self) -> str:
        """🚀 获取或创建用于挂载演化成果的虚拟根文档"""
        SOVEREIGN_HASH = "SOVEREIGN_EVOLUTION_ROOT"
        existing_id = await self.find_document_by_hash(SOVEREIGN_HASH)
        if existing_id: 
            return existing_id
        
        # 🚀 物理确权：不存在则创建
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{self.tables['documents']['id']}/records"
        fields = {
            "文件名": "云端主权演化共识库.sovereign",
            "文件哈希": SOVEREIGN_HASH,
            "处理状态": "COMPLETED",
            "总页数": 1
        }
        resp = await self._api_request("POST", url, json_data={"fields": fields})
        return resp.get("data", {}).get("record", {}).get("record_id", "")

    async def save_chunks_batch(self, doc_rec_id: str, chunks: List[Dict[str, Any]]) -> List[str]:
        table_id = self.tables['chunks']['id']
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/batch_create"
        
        created_ids = []
        for i in range(0, len(chunks), 100):
            batch = chunks[i:i+100]
            records = []
            for c in batch:
                content = c.get("content", "")
                fields = {
                    "文档关联": str(doc_rec_id), 
                    "正文内容": content,
                    "物理页码": c.get("page_number", 0),
                    "逻辑坐标": c.get("logic_coord", f"P{c.get('page_number', 0)}-{hashlib.md5(content.encode()).hexdigest()[:8]}"),
                    "逻辑面包屑": c.get("breadcrumb", ""),
                    "逻辑指纹": hashlib.md5(content.encode()).hexdigest(),
                    "Git版本": "v2.0-cloud",
                    "元数据": json.dumps(c.get("metadata_json", {})) if c.get("metadata_json") else "",
                    "父级关联": c.get("parent_id") if isinstance(c.get("parent_id"), list) else ([c["parent_id"]] if c.get("parent_id") else []),
                    "记忆ID": str(c.get("memory_id", ""))
                }

                records.append({"fields": fields})
            
            resp = await self._api_request("POST", url, {"records": records})
            items = resp.get("data", {}).get("records", [])
            created_ids.extend([it.get("record_id") for it in items])
        return created_ids

    async def backfill_consensus(self, records: List[Dict[str, Any]]):
        """
        🚀 [V160.0] 物理回填：直接将精加工的客观共识写入 Bitable。
        不进行二次加工，确保主权钢印不丢失。
        """
        # 🛡️ 架构师守则：强制使用物理常量 ID，杜绝环境污染。
        table_id = "tblgTgxUGTUykcU2" 
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/batch_create"
        
        # 包装为 Bitable 标准格式
        payload = {"records": [{"fields": r} for r in records]}
        
        resp = await self._api_request("POST", url, json_data=payload)
        if resp.get("code") == 0:
            print(f"✅ [BitableLedger] 成功物理回填 {len(records)} 条主权演化共识。")
        else:
            logger.error(f"❌ [BitableLedger] 回填失败: {resp.get('msg')} | Payload: {json.dumps(payload, ensure_ascii=False)[:500]}...")

    async def save_toc_items_batch(self, doc_rec_id: str, toc_items: List[Dict[str, Any]]):
        """批量保存脊梁结构"""
        table_id = self.tables['toc']['id']
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/batch_create"
        
        for i in range(0, len(toc_items), 100):
            batch = toc_items[i:i+100]
            records = []
            for item in batch:
                records.append({"fields": {
                    "标题": item.get("title", ""),
                    "层级": item.get("level", 0),
                    "逻辑页码": item.get("logical_page", 0),
                    "文档关联": str(doc_rec_id),
                    "逻辑坐标": f"TOC-L{item.get('level', 0)}-P{item.get('logical_page', 0)}"
                }})
            await self._api_request("POST", url, {"records": records})

    async def wait_for_completion(self, doc_rec_id: str, expected_chunk_ids: List[str], timeout: int = 300) -> List[Dict[str, Any]]:
        """
        🛡️ 语义反哺确权：轮询捕获 Bitable AI 生成的“逻辑摘要”与“语义标签”。
        """
        table_id = self.tables['chunks']['id']
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/search"
        payload = {
            "filter": {"conjunction": "and", "conditions": [{"field_name": "文档关联", "operator": "is", "value": [doc_rec_id]}]},
            "page_size": 500
        }
        
        start_time = asyncio.get_event_loop().time()
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            resp = await self._api_request("POST", url, json_data=payload)
            items = resp.get("data", {}).get("items", [])
            
            # 🚀 物理确权：只筛选本次确权的 ID
            current_items = [it for it in items if it.get("record_id") in expected_chunk_ids]
            
            # 检查 AI 字段是否已全部孵化（摘要 + 标签）
            ready_items = []
            for it in current_items:
                f = it.get("fields", {})
                if f.get("逻辑摘要") and f.get("语义标签"):
                    ready_items.append(it)
            
            if len(ready_items) >= len(expected_chunk_ids) and len(expected_chunk_ids) > 0:
                print(f"  ↳ 云端 AI 孵化完成：{len(ready_items)} 个分片已捕获摘要与标签。")
                
                results = []
                for it in ready_items:
                    f = it.get("fields", {})
                    # 处理多选标签：Bitable 返回可能是对象列表或字符串列表
                    raw_tags = f.get("语义标签", [])
                    tags = [t if isinstance(t, str) else t.get("text", "") for t in raw_tags] if isinstance(raw_tags, list) else [str(raw_tags)]
                    
                    results.append({
                        "id": it["record_id"],
                        "doc_record_id": doc_rec_id,
                        "summary": self._plain_text(f.get("逻辑摘要", "")),
                        "content": self._plain_text(f.get("正文内容", "")),
                        "logic_tags": tags,
                        "embedding": json.loads(f.get("向量表征", "null")) if f.get("向量表征") else None
                    })
                return results
            
            print(f"  ↳ 等待云端 AI 孵化摘要与标签... ({len(ready_items)}/{len(expected_chunk_ids)})")
            await asyncio.sleep(8)
        return []

    async def update_chunk_fields(self, chunk_rec_id: str, fields: Dict[str, Any]):
        """通用分片字段回填"""
        table_id = self.tables['chunks']['id']
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/{chunk_rec_id}"
        await self._api_request("PUT", url, {"fields": fields})

    async def update_document_status(self, doc_rec_id: str, status: str):
        table_id = self.tables['documents']['id']
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/{doc_rec_id}"
        await self._api_request("PUT", url, {"fields": {"处理状态": status}})

    async def fetch_chunks_by_galaxy(self, galaxy_rec_id: str) -> List[Dict]:
        table_id = self.tables['chunks']['id']
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/search"
        payload = {"filter": {"conjunction": "and", "conditions": [{"field_name": "星系关联", "operator": "contains", "value": [galaxy_rec_id]}]}}
        resp = await self._api_request("POST", url, json_data=payload)
        items = resp.get("data", {}).get("items", [])
        return [{
            "id": it["record_id"],
            "doc_record_id": self._extract_record_id(it["fields"].get("文档关联")),
            "summary": self._plain_text(it["fields"].get("逻辑摘要", "")),
            "content": self._plain_text(it["fields"].get("正文内容", ""))
        } for it in items]

    async def search_chunks(self, query: str = "", 
                            doc_record_id: Optional[str] = None, 
                            galaxy_ids: Optional[List[str]] = None,
                            tags: Optional[List[str]] = None,
                            limit: int = 50) -> List[Dict]:
        """
        🚀 [V150.0] 反向主权会师：从星系反向收割分片，彻底解决物理过滤失效。
        """
        clean_table_id = str(self.tables['chunks']['id']).strip()
        
        # 1. 物理定位：获取领地内的所有分片 ID
        target_chunk_ids = []
        if galaxy_ids:
            gal_table = self.tables['galaxies']['id']
            # 我们逐个读取星系领地（通常只有 1-3 个）
            for gid in galaxy_ids:
                url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{gal_table}/records/{gid}"
                resp = await self._api_request("GET", url)
                f = resp.get("data", {}).get("record", {}).get("fields", {})
                # 提取反向关联字段：Bitable 默认名为 Chunks-星系关联 或 星系关联
                # 我们优先检查 manifest 中定义的字段名或常见反向链接名
                chunk_links = f.get("Chunks-星系关联") or f.get("星系关联")
                ids = self._extract_record_id(chunk_links)
                target_chunk_ids.extend(ids)
        
        # 2. 精准收割：并发拉取分片正文
        if not target_chunk_ids:
            print("⚠️ [search_chunks] 领地内无分片 ID 索引。")
            return []

        # 🚀 物理确权：对 ID 列表执行并发 GET，绕过不稳定的 search 接口
        target_chunk_ids = list(set(target_chunk_ids))[:limit]
        print(f"📡 [DirectHarvest] 正在并发收割 {len(target_chunk_ids)} 条分片...")
        
        tasks = []
        for cid in target_chunk_ids:
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{clean_table_id}/records/{cid}"
            tasks.append(self._api_request("GET", url))
            
        resps = await asyncio.gather(*tasks)
        
        results = []
        for resp in resps:
            if resp.get("code") == 0:
                it = resp.get("data", {}).get("record", {})
                f = it.get("fields", {})
                
                # 🚀 物理确权：显式解析星系关联 ID
                g_links = f.get("星系关联")
                g_ids = self._extract_record_id(g_links)

                results.append({
                    "id": it["record_id"],
                    "summary": self._plain_text(f.get("逻辑摘要", "")),
                    "content": self._plain_text(f.get("正文内容", "")),
                    "logic_tags": f.get("语义标签", []),
                    "breadcrumb": self._plain_text(f.get("逻辑面包屑", "")),
                    "page_number": f.get("物理页码", 0),
                    "galaxy_ids": g_ids  # 🚀 回填星系座标
                })
        
        print(f"📦 [DirectHarvest] 物理刺杀完成，成功收割 {len(results)} 条带座标证据。")
        return results

bitable_ledger = BitableLedger()
