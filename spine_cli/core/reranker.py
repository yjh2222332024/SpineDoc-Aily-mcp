
import numpy as np
import httpx
import asyncio
from typing import List, Dict, Any, Optional
from app.core.config import settings

class SpineReranker:
    """
    SpineDoc 深度重排器 (V4.1 云端加速版)
    优先调用 SiliconFlow API 执行重排，无需下载本地大模型。
    """
    def __init__(self):
        # 🏛️ 架构侦测：检测是否具备云端 Rerank 能力
        self.api_key = settings.EMBEDDING_API_KEY
        self.api_url = "https://api.siliconflow.cn/v1/rerank"
        self.model_name = "BAAI/bge-reranker-v2-m3"
        
        # 只有配置了 API_KEY 且 URL 匹配时才开启
        self.enabled = self.api_key is not None and "siliconflow" in settings.EMBEDDING_BASE_URL.lower()
        if self.enabled:
            print(f"DEBUG: Cloud Reranker enabled (SiliconFlow). Model={self.model_name}")
        else:
            print("DEBUG: Cloud Reranker disabled (Check EMBEDDING_API_KEY in .env).")

    async def rerank(self, query: str, chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        🚀 执行异步云端重排序
        """
        if not self.enabled or not chunks:
            return chunks[:top_k]

        documents = [c.get("text", c.get("content", "")) for c in chunks]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model_name,
            "query": query,
            "documents": documents,
            "top_n": len(documents),
            "return_documents": False
        }
        
        try:
            # 🏛️ 架构师建议：使用 30s 超时，确保 API 调用的稳定性
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(self.api_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                
                # SiliconFlow 返回格式: {"results": [{"index": 0, "relevance_score": 0.9}, ...]}
                for res_item in data.get("results", []):
                    idx = res_item["index"]
                    score = res_item["relevance_score"]
                    chunks[idx]["rerank_score"] = float(score)
            
            # 排序并截断
            reranked = sorted(chunks, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
            return reranked[:top_k]
            
        except Exception as e:
            print(f"❌ Cloud Rerank failed: {e}")
            # 兜底返回原始结果（按向量距离排过序的）
            return chunks[:top_k]

    # 为了保持向后兼容，提供一个同步封装接口
    def rerank_sync(self, query: str, chunks: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        try:
            # 🏛️ 架构注意：在 CLI 环境下，我们可能需要这种同步封装
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.rerank(query, chunks, top_k))
        except:
            return chunks[:top_k]
