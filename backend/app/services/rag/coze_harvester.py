"""
⚠️ DEPRECATED - SpineDoc Coze 云端收割机 (CozeHarvester)
==============================================
职责：此模块已废弃。云端语义撞击统一由 AilyHarvester 接管。
"""

import asyncio
import httpx
import json
import logging
from typing import List, Dict, Any, Optional
from backend.app.services.keyword_extractor import get_keyword_extractor
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class CozeHarvester:
    """
    CozeHarvester: Cloud semantic search via Coze Workflow API.
    """
    def __init__(self, store=None):
        from backend.app.services.feishu.bitable_ledger import bitable_ledger
        self.extractor = get_keyword_extractor()
        self.store = store or bitable_ledger
        self.api_key = settings.COZE_API_KEY
        self.workflow_id = settings.COZE_WORKFLOW_ID
        self.rrf_k = 60

    async def harvest(self, 
                      query: str, 
                      doc_record_id: Optional[str] = None, 
                      limit: int = 10) -> List[Dict]:
        """
        🚀 核心逻辑：通过 Coze Workflow 执行语义撞击
        """
        if not self.api_key or not self.workflow_id:
            print("⚠️ [CozeHarvester] COZE_API_KEY 或 WORKFLOW_ID 未配置，降级到本地模式。")
            return []

        print(f"📡 [Coze] 正在通过 API 发起语义撞击请求: '{query[:20]}...'")

        # 1. 提取 Query 关键词 (用于 Bitable 侧混合碰撞)
        query_tags = self.extractor.extract_keywords(query, top_n=10)
        
        # 2. 并行双路检索
        # A 路径：Coze Workflow API (云端向量撞击)
        # B 路径：Bitable 标签碰撞 (云端标签收割)
        tasks = [
            self._call_coze_workflow(query),
            self.store.search_chunks(query, doc_record_id=doc_record_id, tags=query_tags, limit=limit * 2)
        ]
        
        coze_results, tag_results = await asyncio.gather(*tasks)
        
        # 3. RRF 排名融合
        all_hits = {}
        
        # 处理 Coze 向量路径
        for rank, hit in enumerate(coze_results, 1):
            # 映射 Coze 输出到 SpineDoc 契约
            # 假设 Coze 工作流返回的是包含 content, record_id 等字段的列表
            h_id = hit.get("record_id") or hit.get("id")
            if not h_id: continue
            
            if h_id not in all_hits:
                all_hits[h_id] = {
                    "id": h_id,
                    "content": hit.get("content", ""),
                    "page_number": hit.get("page_number", 0),
                    "found_by_coze": True
                }
            all_hits[h_id]["rrf_score"] = all_hits[h_id].get("rrf_score", 0.0) + (1.0 / (self.rrf_k + rank))

        # 处理标签碰撞路径
        for rank, hit in enumerate(tag_results, 1):
            h_id = hit["id"]
            if h_id not in all_hits: all_hits[h_id] = hit
            all_hits[h_id]["rrf_score"] = all_hits[h_id].get("rrf_score", 0.0) + (1.0 / (self.rrf_k + rank))
            all_hits[h_id]["found_by_tags"] = True

        final_results = sorted(all_hits.values(), key=lambda x: x.get("rrf_score", 0.0), reverse=True)
        print(f"✅ [CozeHarvester] 云端撞击完成，融合结果数: {len(final_results)}")
        
        return final_results[:limit]

    async def _call_coze_workflow(self, query: str) -> List[Dict]:
        """封装 Coze Workflow API 调用"""
        url = "https://api.coze.cn/v1/workflow/run"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "workflow_id": self.workflow_id,
            "parameters": {"query": query}
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    # 🚀 [V60.0] Coze 返回的是字符串化的 data 字段，需要二次解析
                    raw_data = data.get("data", "[]")
                    try:
                        return json.loads(raw_data) if isinstance(raw_data, str) else raw_data
                    except:
                        return []
                else:
                    logger.error(f"❌ [Coze] API 请求失败: {resp.text}")
                    return []
            except Exception as e:
                logger.error(f"❌ [Coze] 通信异常: {e}")
                return []

coze_harvester = CozeHarvester()
