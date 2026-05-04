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
        if not texts: return []
        
        clean_texts = [self._sanitize_text(t) for t in texts]
        
        # 🚀 [V140.0] 回归智谱：使用智谱 V4 标准向量接口
        # 智谱的 Embedding-3 支持 256/512/1024/2048 维度
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model_name,
            "input": clean_texts
            # 注意：智谱标准接口不带 late_chunking 参数
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                # 智谱的路径通常是 /embeddings，但 base_url 可能已经包含了 v4/
                url = f"{self.base_url}/embeddings"
                resp = await client.post(url, json=payload, headers=headers)
                
                if resp.status_code != 200:
                    logger.error(f"❌ [Zhipu-Embedding] API 错误: {resp.text}")
                    raise Exception(f"Embedding API failed: {resp.status_code}")
                    
                data = resp.json()
                # 智谱的返回结构是 {"data": [{"embedding": [...], "index": 0}, ...]}
                # 我们按索引排序以确保顺序正确（虽然通常就是顺序的）
                sorted_data = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
                return [item["embedding"] for item in sorted_data]
            except Exception as e:
                logger.error(f"❌ [Zhipu-Embedding] 通信异常: {e}")
                raise

embedding_service = EmbeddingService()
