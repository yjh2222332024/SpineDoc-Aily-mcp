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

# 🚀 [RateLimit] 全局信号量，防止触发飞书熔断
_rate_limiter = asyncio.Semaphore(10)  # 最大 10 并发（更保守）
_retry_delay = 0.3  # 初始重试延迟（秒）

# 🚀 [Cache] 请求去重缓存，同一 chunk 5 秒内不重复拉取
_chunk_cache: Dict[str, tuple[float, Dict]] = {}  # {record_id: (timestamp, data)}
_cache_ttl = 5.0  # 缓存 5 秒

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

    async def _api_request(self, method: str, url: str, json_data: Dict = None, params: Dict = None, max_retries: int = 3) -> Dict:
        # 🛡️ 架构师守则：URL 必须是纯净的。现场打印最终物理座标。
        print(f"DEBUG_FINAL_URL: {url}")

        for attempt in range(max_retries):
            try:
                async with _rate_limiter:  # 🚀 全局并发控制
                    token = await self.auth.get_tenant_access_token()
                    async with httpx.AsyncClient(trust_env=False, timeout=30.0) as client:
                        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
                        resp = await client.request(method, url, json=json_data, params=params, headers=headers)
                        data = resp.json()

                        # 🚀 [RateLimit] 检测熔断
                        if data.get("code") == 99991663 or "frequency limit" in str(data.get("msg", "")).lower():
                            if attempt < max_retries - 1:
                                wait = _retry_delay * (2 ** attempt)  # 指数退避
                                logger.warning(f"⚠️ [Bitable-API] 触发限流，等待 {wait:.1f}s 后重试 ({attempt + 1}/{max_retries})")
                                await asyncio.sleep(wait)
                                continue

                        if data.get("code") != 0:
                            logger.error(f"❌ [Bitable-API] Failed: {data.get('msg')} | URL: {url}")
                        return data

            except Exception as e:
                if attempt < max_retries - 1:
                    wait = _retry_delay * (2 ** attempt)
                    logger.warning(f"⚠️ [Bitable-API] 网络异常 {e}，等待 {wait:.1f}s 后重试")
                    await asyncio.sleep(wait)
                    continue
                raise

        return {"code": -1, "msg": "max retries exceeded"}

    async def _get_app_token(self) -> str:
        return await self.auth.get_wiki_obj_token()

    def _extract_record_id(self, field_value: Any) -> List[str]:
        """
        🚀 [V155.0] 物理提取强化：全兼容 Bitable Link 字段
        支持：Bare record_id, {"link_record_ids": []}, [{"record_ids": []}, ...]
        """
        if not field_value:
            return []

        # 格式 A: {'link_record_ids': ['recxxx', ...]}
        if isinstance(field_value, dict) and "link_record_ids" in field_value:
            return [str(i) for i in field_value["link_record_ids"]]

        # 格式 B: 单个字符串 "recxxx"
        if isinstance(field_value, str):
            return [field_value] if field_value else []

        # 格式 C: [{'record_ids': ['recxxx', ...]}, ...] - Bitable 反向关联
        if isinstance(field_value, list):
            res = []
            for item in field_value:
                if isinstance(item, dict):
                    if "record_ids" in item:
                        res.extend([str(i) for i in item["record_ids"]])
                    elif "id" in item:
                        res.append(str(item["id"]))
                    elif "record_id" in item:
                        res.append(str(item["record_id"]))
                elif isinstance(item, str):
                    res.append(item)
            return [r for r in res if r and r.startswith("rec")]

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

        # 尝试完整格式
        payload = {"records": [{"fields": r} for r in records]}

        resp = await self._api_request("POST", url, json_data=payload)
        if resp.get("code") == 0:
            print(f"✅ [BitableLedger] 成功物理回填 {len(records)} 条主权演化共识。")
            return

        # 若失败，降级为纯文本字段（去掉关联字段）
        logger.warning(f"⚠️ [BitableLedger] 回填失败 ({resp.get('msg')})，降级重试...")
        fallback_records = []
        for r in records:
            fallback = {k: v for k, v in r.items()
                       if k not in ("星系关联", "文档关联", "父级关联")}
            fallback_records.append(fallback)

        fallback_payload = {"records": [{"fields": r} for r in fallback_records]}
        resp2 = await self._api_request("POST", url, json_data=fallback_payload)
        if resp2.get("code") == 0:
            print(f"✅ [BitableLedger] 成功物理回填 {len(fallback_records)} 条（降级模式）。")
        else:
            logger.error(f"❌ [BitableLedger] 降级回填也失败: {resp2.get('msg')}")

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

    async def list_documents(self) -> List[Dict]:
        """🚀 [V220.0] 列出所有文档记录"""
        table_id = self.tables['documents']['id']
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records"
        resp = await self._api_request("GET", url)
        items = resp.get("data", {}).get("items", [])
        results = []
        for it in items:
            f = it.get("fields", {})
            results.append({
                "id": it["record_id"],
                "filename": f.get("文件名", "Unknown"),
                "file_hash": f.get("文件哈希", ""),
                "status": f.get("处理状态", ""),
                "total_pages": f.get("总页数", 0),
            })
        return results

    async def fetch_chunks_by_document(self, doc_record_id: str, limit: int = 50) -> List[Dict]:
        """🚀 [V220.0] 物理确权：从 documents 表下路，直接收割分片。"""
        table_id = self.tables['chunks']['id']
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{table_id}/records/search"
        payload = {
            "filter": {
                "conjunction": "and",
                "conditions": [{"field_name": "文档关联", "operator": "is", "value": [doc_record_id]}]
            },
            "page_size": limit
        }
        resp = await self._api_request("POST", url, json_data=payload)
        items = resp.get("data", {}).get("items", [])
        results = []
        for it in items[:limit]:
            f = it.get("fields", {})
            results.append({
                "id": it["record_id"],
                "doc_record_id": doc_record_id,
                "summary": self._plain_text(f.get("逻辑摘要", "")),
                "content": self._plain_text(f.get("正文内容", "")),
                "logic_tags": f.get("语义标签", []),
                "breadcrumb": self._plain_text(f.get("逻辑面包屑", "")),
                "page_number": f.get("物理页码", 0),
            })
        return results

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
        
        # 2. 精准收割：并发拉取分片正文（带去重缓存）
        if not target_chunk_ids:
            print("⚠️ [search_chunks] 领地内无分片 ID 索引。")
            return []

        # 🚀 [Dedupe] 去重：过滤掉 5 秒内已缓存的 chunk
        results = []  # 🚀 初始化 results
        now = asyncio.get_event_loop().time()
        new_cids = []
        for cid in target_chunk_ids:
            if cid in _chunk_cache:
                cached_time, cached_data = _chunk_cache[cid]
                if now - cached_time < _cache_ttl:
                    results.append(cached_data)  # 直接用缓存
                    continue
            new_cids.append(cid)
        target_chunk_ids = new_cids

        if not target_chunk_ids:
            print(f"📦 [DirectHarvest] 全部命中缓存，返回 {len(results)} 条带座标证据。")
            return results

        # 🚀 物理确权：对 ID 列表执行并发 GET（先去重）
        unique_cids = list(set(target_chunk_ids))[:limit]
        print(f"📡 [DirectHarvest] 正在并发收割 {len(unique_cids)} 条分片...")
        
        tasks = []
        for cid in unique_cids:
            url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.app_token}/tables/{clean_table_id}/records/{cid}"
            tasks.append(self._api_request("GET", url))
            
        resps = await asyncio.gather(*tasks)

        for resp in resps:
            if resp.get("code") == 0:
                it = resp.get("data", {}).get("record", {})
                f = it.get("fields", {})

                # 🚀 物理确权：显式解析星系关联 ID
                g_links = f.get("星系关联")
                g_ids = self._extract_record_id(g_links)

                chunk_data = {
                    "id": it["record_id"],
                    "summary": self._plain_text(f.get("逻辑摘要", "")),
                    "content": self._plain_text(f.get("正文内容", "")),
                    "logic_tags": f.get("语义标签", []),
                    "breadcrumb": self._plain_text(f.get("逻辑面包屑", "")),
                    "page_number": f.get("物理页码", 0),
                    "galaxy_ids": g_ids  # 🚀 回填星系座标
                }
                # 🚀 [Cache] 写入缓存
                _chunk_cache[it["record_id"]] = (now, chunk_data)
                results.append(chunk_data)
        
        print(f"📦 [DirectHarvest] 物理刺杀完成，成功收割 {len(results)} 条带座标证据。")
        return results

bitable_ledger = BitableLedger()
