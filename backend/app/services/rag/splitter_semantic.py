"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - Advanced Structural RAG
Author: Yan Junhao (严俊皓)
License: Private / Proprietary (Unauthorized copying is strictly prohibited)
"""
from typing import List, Dict, Any
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import re
from backend.app.services.rag.embedding import embedding_service

class SemanticSplitter:
    """
    语义感知切片器 (Deep Semantic Splitter) - V50.4 单例对齐版
    
    不按字数切，按“意思”切。
    🚀 [V50.4] 核心升级：复用 EmbeddingService (BGE-M3)，实现 100% 本地化与资源零浪费。
    """

    def __init__(self, threshold: float = 0.45):
        """
        Args:
            threshold: 相似度阈值 (针对 BGE-M3 调优，建议 0.4-0.5)
        """
        self.threshold = threshold
        print(f"🚀 [Splitter] 语义切片引擎已就绪 (复用后端 BGE-M3)")

    async def split_text(self, text: str, min_chunk_len: int = 150) -> List[str]:
        """
        对长文本进行语义切片。
        min_chunk_len: 最小字符数，防止切得太碎导致丢失上下文。
        """
        # 1. 句子分割
        sentences = re.split(r'(?<=[。！？.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if len(sentences) <= 1:
            return sentences

        # 2. 🚀 使用单例服务获取 Embeddings (自动加速/降级)
        embeddings_list = await embedding_service.get_embeddings(sentences)
        embeddings = np.array(embeddings_list)

        # 3. 计算相邻句子的相似度
        breaks = []
        current_chunk_len = 0
        for i in range(len(embeddings) - 1):
            current_chunk_len += len(sentences[i])
            sim = cosine_similarity([embeddings[i]], [embeddings[i+1]])[0][0]
            
            # 只有当相似度低 且 当前累积长度达到最小值时，才允许切分
            if sim < self.threshold and current_chunk_len >= min_chunk_len:
                breaks.append(i + 1)
                current_chunk_len = 0
        
        # 4. 根据断点组装 Chunks
        chunks = []
        start_idx = 0
        for end_idx in breaks:
            chunk = " ".join(sentences[start_idx:end_idx])
            chunks.append(chunk)
            start_idx = end_idx
        
        last_chunk = " ".join(sentences[start_idx:])
        if last_chunk:
            chunks.append(last_chunk)

        return chunks

# 单例导出 (注意：模型加载可能较慢，建议懒加载或启动时加载)
# semantic_splitter = SemanticSplitter() 
