"""
SpineDoc 脊梁分片器 (SpineSplitter) - 2026/04/11 锋利版
================================================
职责：实现高敏感度的语义断点检测，确保切片能够精准捕捉话题转折。
"""
import re
import uuid
import numpy as np
from typing import List, Dict, Any
from .embedding import embedding_service
from .logic_refiner import LogicRefiner

class SpineSplitter:
    def __init__(self, threshold: float = 0.82, max_tokens: int = 800):
        # 🚀 [V47.1] 调优：BGE-Small 的语义突变通常在 0.8 以下
        self.threshold = threshold
        self.max_tokens = max_tokens
        self.refiner = LogicRefiner()

    async def split_chapter_stream(self, 
                                   text: str, 
                                   toc_item_id: str, 
                                   breadcrumb: str) -> List[Dict[str, Any]]:
        """
        🚀 核心：利用高灵敏度向量对比寻找语义断层。
        """
        # 1. 句子分割
        sentences = [s.strip() for s in re.split(r'(?<=[。！？.!?])\s+', text) if len(s.strip()) > 5]
        if not sentences: return []
        if len(sentences) == 1:
            return [await self._package_chunk(sentences[0], toc_item_id, breadcrumb)]

        # 2. 批量向量化 (CPU 高并发)
        embeddings = await embedding_service.get_embeddings(sentences)
        embs = np.array(embeddings)
        
        # 计算相邻相似度
        norm = np.linalg.norm(embs, axis=1)
        norm[norm == 0] = 1e-9
        embs_norm = embs / norm[:, np.newaxis]
        similarities = np.sum(embs_norm[:-1] * embs_norm[1:], axis=1)

        # 3. 执行灵敏切割
        chunks = []
        current_sentences = []
        current_len = 0
        
        for i, sim in enumerate(similarities):
            current_sentences.append(sentences[i])
            current_len += len(sentences[i])
            
            # 🚀 [策略]：语义突变 (sim < threshold) 或者 长度溢出
            # 只要语义断了，且当前已经有一定内容(>50字)，就切！
            if (sim < self.threshold and current_len > 50) or current_len > self.max_tokens:
                # print(f"✂️ [Splitter] 发现断层 (Sim: {sim:.4f}), 执行切分。")
                chunk_text = " ".join(current_sentences)
                chunks.append(await self._package_chunk(chunk_text, toc_item_id, breadcrumb))
                current_sentences = []
                current_len = 0
        
        # 补齐尾部
        current_sentences.append(sentences[-1])
        chunk_text = " ".join(current_sentences)
        chunks.append(await self._package_chunk(chunk_text, toc_item_id, breadcrumb))

        return chunks

    async def _package_chunk(self, content: str, toc_id: str, breadcrumb: str) -> Dict[str, Any]:
        # 暂时只做基础包装，KeyBERT 留待下一步
        return {
            "id": str(uuid.uuid4()),
            "content": content,
            "toc_item_id": toc_id,
            "breadcrumb": breadcrumb,
            "logic_tags": [], # 待填充
            "summary": "",    # 待填充
            "metadata_json": {"split_method": "semantic_v2"}
        }
