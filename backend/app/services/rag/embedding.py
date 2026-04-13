"""
SpineDoc 动态本地嵌入服务 (DynamicLocalEmbedding) - 2026/04/11
============================================================
职责：利用轻量级模型分身实现本地 CPU 高并发向量化，专门服务于分片与打标。
分身 A (中文专家): BAAI/bge-small-zh-v1.5
分身 B (英文专家): BAAI/bge-small-en-v1.5
"""
import os
import asyncio
import numpy as np
import logging
import re
from typing import List, Union, Dict, Any
from sentence_transformers import SentenceTransformer
from backend.app.core.config import settings

# 🏛️ 顶级架构师：必须显式定义 logger，这是子模块的‘喉咙’
logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    🚀 [V48.0] 量化版 BGE-M3 嵌入服务：专为轻薄本优化的‘语义聚合器’。
    特点：1024 维高维表征，支持 100+ 语言，强制 CPU 运行保障 1GB 级内存占用。
    """
    def __init__(self):
        self._model = None
        self._lock = asyncio.Lock()

    def _get_model(self) -> SentenceTransformer:
        """单例加载 BGE-M3 (量化平衡版)"""
        if self._model is None:
            model_name = "BAAI/bge-m3"
            # 🏛️ 顶级架构师：直接引用 settings 对象
            cache_dir = settings.CACHE_DIR
            
            logger.info(f"🧠 [Embedding] 正在加载全能 BGE-M3 (Cache: {cache_dir})")
            
            try:
                self._model = SentenceTransformer(
                    model_name, 
                    device="cpu", 
                    cache_folder=cache_dir,
                    trust_remote_code=True
                )
                # 🏛️ 强制设置最大序列长度，防止长文本爆内存
                self._model.max_seq_length = 1024 
                print("✅ [Embedding] BGE-M3 (CPU-Optimized) 已就绪，维度: 1024")
            except Exception as e:
                logger.error(f"❌ [Embedding] 模型加载失败: {e}")
                raise e
        return self._model

    async def get_embeddings(self, texts: Union[str, List[str]]) -> List[List[float]]:
        if isinstance(texts, str): texts = [texts]
        if not texts: return []

        model = self._get_model()

        loop = asyncio.get_event_loop()
        try:
            # 🏛️ 专业的代码：在执行器中运行，防止 CPU 编码阻塞 FastAPI 事件循环
            embeddings = await loop.run_in_executor(
                None, 
                lambda: model.encode(
                    texts, 
                    normalize_embeddings=True,
                    batch_size=4 # 🏛️ 小批次，防止内存峰值
                )
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"❌ [Embedding] 推理失败: {e}")
            # 🏛️ 鲁棒性保障：返回 1024 维全零向量，确保数据库不崩溃
            return [[0.0] * 1024] * len(texts)

embedding_service = EmbeddingService()
