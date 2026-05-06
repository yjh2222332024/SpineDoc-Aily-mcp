"""
ZhipuHarvester - White-box Cloud Retrieval Service
==================================================
Responsibility:
1. Execute multi-path (vector + keyword) retrieval via Zhipu AI.
2. Capture raw recall and rerank scores for logic court.
3. Apply metadata filtering to enforce galaxy sovereignty.
"""

import httpx
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class ZhipuHarvester:
    """
     [V120.0] 智谱白盒收割机：工业级云端检索算力。
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ZHIPU_API_KEY
        self.base_url = "https://open.bigmodel.cn/api/paas/v4/knowledge"
        self.timeout = 30.0

    async def _api_request(self, method: str, endpoint: str, payload: Dict) -> Dict:
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.request(method, url, json=payload, headers=headers)
            if resp.status_code != 200:
                logger.error(f" [Zhipu-API] Failed: {resp.text}")
                return {}
            return resp.json()

    async def harvest(self, 
                      query: str, 
                      knowledge_id: str, # 智谱侧的知识库 ID
                      galaxy_ids: Optional[List[str]] = None,
                      limit: int = 10) -> List[Dict]:
        """
         执行白盒收割
        """
        print(f" [ZhipuHarvester] 启动白盒收割: {query[:20]} | 知识库: {knowledge_id}")
        
        # 1. 构造过滤条件（主权领地限制）
        filter_data = {}
        if galaxy_ids:
            # 假设我们在上传切片到智谱时，在 metadata 中注入了 galaxy_id
            filter_data = {
                "field": "metadata.galaxy_id",
                "operator": "IN",
                "values": galaxy_ids
            }

        payload = {
            "knowledge_id": knowledge_id,
            "query": query,
            "top_k": limit,
            "search_type": "mixed", # 混合检索：向量 + 关键词
            "filter": filter_data if filter_data else None
        }

        #  物理质询：调用智谱检索 API
        resp = await self._api_request("POST", "search", payload)
        
        # 2. 逻辑收割
        hits = resp.get("list", [])
        print(f" [ZhipuHarvester] 收割完成，发现 {len(hits)} 条原始证据。")
        
        results = []
        for hit in hits:
            # 捕获白盒得分
            recall_score = hit.get("recall_score", 0.0)
            rerank_score = hit.get("rerank_score", 0.0)
            
            results.append({
                "id": hit.get("id"),
                "content": hit.get("content", ""),
                "summary": hit.get("metadata", {}).get("summary", ""),
                "score": rerank_score or recall_score,
                "recall_score": recall_score,
                "rerank_score": rerank_score,
                "source": hit.get("metadata", {}).get("file_name", "Unknown"),
                "found_by": "zhipu_mixed"
            })
        
        return results

zhipu_harvester = ZhipuHarvester()
