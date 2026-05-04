"""
ZhipuReranker - Cloud-powered Semantic Reranking
===============================================
Responsibility:
1. Send candidate documents to Zhipu AI for deep semantic reranking.
2. Return high-precision scores without requiring data sync.
"""

import httpx
import logging
import asyncio
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class ZhipuReranker:
    """
    🚀 [V130.1] 智谱重排专家：借用云端算力，无需数据同步。
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ZHIPU_API_KEY
        # 🛡️ 架构师校对：智谱标准重排接口
        self.url = "https://open.bigmodel.cn/api/paas/v4/rerank"
        self.timeout = 20.0

    async def rerank(self, query: str, documents: List[str]) -> List[Dict[str, Any]]:
        """
        🚀 质询云端：对候选文档进行重排序
        """
        if not documents: return []
        
        payload = {
            "model": "rerank", # 智谱标准重排模型
            "query": query,
            "documents": documents,
            "top_n": len(documents)
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(self.url, json=payload, headers=headers)
                if resp.status_code != 200:
                    logger.error(f"❌ [Zhipu-Rerank] Failed: {resp.text}")
                    return []
                
                data = resp.json()
                return data.get("results", [])
        except Exception as e:
            logger.error(f"⚠️ [Zhipu-Rerank] 异常: {e}")
            return []

zhipu_reranker = ZhipuReranker()
