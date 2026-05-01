"""
SpineDoc Cloud Embedding Service (Native CURL-like REST)
======================================================
职责：使用纯粹的 REST API 调用，零依赖，高度可控，彻底规避 SDK 依赖冲突。
"""
import logging
import httpx
import json
from typing import List, Union, Any
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    🚀 极致轻量：纯 REST 架构，拒绝 SDK 依赖污染。
    """
    def __init__(self):
        self.api_key = settings.EMBEDDING_API_KEY
        self.base_url = settings.EMBEDDING_BASE_URL.rstrip('/')
        self.model_name = settings.EMBEDDING_MODEL_NAME
        self.dimension = int(settings.EMBEDDING_DIMENSION)

    def _sanitize_text(self, item: Any) -> str:
        if isinstance(item, str): return item
        if isinstance(item, dict): return item.get("text", str(item))
        return str(item)

    async def get_embeddings(self, texts: Union[str, List[str]]) -> List[List[float]]:
        if isinstance(texts, str): texts = [texts]
        
        clean_texts = [self._sanitize_text(t) for t in texts]
        
        results = []
        for text in clean_texts:
            url = f"{self.base_url}/embeddings"
            payload = {
                "model": self.model_name,
                "input": text,
                "dimensions": self.dimension
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code != 200:
                    logger.error(f"❌ [Embedding] API 响应错误: {resp.text}")
                    raise Exception(f"Embedding API failed: {resp.status_code}")
                    
                data = resp.json()
                results.append(data["data"][0]["embedding"])
        
        return results

embedding_service = EmbeddingService()
