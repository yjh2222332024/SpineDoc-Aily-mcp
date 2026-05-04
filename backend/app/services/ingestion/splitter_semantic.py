
"""
SpineDoc Cloud Semantic Splitter (V60.0 Cloud-Driven)
====================================================
职责：使用 Jina AI 云端 Embedding 实现语义感知的切片。
特性：零本地模型依赖，利用向量余弦相似度寻找主题断点。
"""

import numpy as np
import re
import logging
from typing import List, Dict, Any
from backend.app.services.ingestion.embedding import embedding_service

logger = logging.getLogger(__name__)

class SemanticSplitter:
    """
    🚀 资深架构师：云端语义切片器
    职责：不按字数切，按“意思”切。通过云端向量计算语义连贯性。
    """

    def __init__(self, threshold: float = 0.45):
        """
        Args:
            threshold: 相似度阈值。Jina-v3 建议 0.4-0.5。
                       低于此值认为发生了主题切换。
        """
        self.threshold = threshold
        logger.info(f"🌐 [Splitter] 云端语义切片引擎就绪 (Threshold: {threshold})")

    async def split_text(self, text: str, min_chunk_len: int = 300) -> List[str]:
        """
        对长文本进行语义切片。
        1. 按句子分割。
        2. 云端获取句子向量。
        3. 计算相邻相似度并寻找断点。
        """
        if not text.strip():
            return []

        # 1. 句子分割 (基于标点符号)
        # 🏛️ 纪律：保留标点，不要让句子在物理上断裂
        sentences = re.split(r'(?<=[。！？.!?])\s*', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 1:
            return sentences

        # 2. 🚀 云端批量获取向量 (一次往返，极致时延)
        try:
            embeddings_list = await embedding_service.get_embeddings(sentences)
            if not embeddings_list:
                return [text]
            embeddings = np.array(embeddings_list)
        except Exception as e:
            logger.error(f"⚠️ [Splitter] 云端向量获取失败，降级为原始文本: {e}")
            return [text]

        # 3. 计算相邻句子的余弦相似度
        # 🏛️ 优化：利用 Numpy 向量化计算，不再使用 sklearn，保持轻量
        breaks = []
        current_chunk_len = 0
        
        # 归一化以简化余弦相似度计算 (点积即相似度)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norm_embeddings = embeddings / (norms + 1e-9)

        for i in range(len(norm_embeddings) - 1):
            current_chunk_len += len(sentences[i])
            
            # 计算相邻句子的相似度
            sim = np.dot(norm_embeddings[i], norm_embeddings[i+1])
            
            # 只有当相似度低 且 当前累积长度达到最小值时，才允许切分
            if sim < self.threshold and current_chunk_len >= min_chunk_len:
                breaks.append(i + 1)
                current_chunk_len = 0
        
        # 4. 根据断点组装 Chunks
        chunks = []
        start_idx = 0
        for end_idx in breaks:
            chunk = "".join(sentences[start_idx:end_idx])
            chunks.append(chunk)
            start_idx = end_idx
        
        last_chunk = "".join(sentences[start_idx:])
        if last_chunk:
            chunks.append(last_chunk)

        return chunks
