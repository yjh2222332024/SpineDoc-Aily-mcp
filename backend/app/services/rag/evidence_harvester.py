"""
SpineDoc 证据收割机 (EvidenceHarvester) - V2.0 SOTA版
======================================================
职责：利用 RRF (Reciprocal Rank Fusion) 排名融合算法，
     整合向量检索、标签碰撞与 TOC 物理先验，提供高性能、高确定性的原始证据流。
架构：卑微的机械装置，仅负责召回与初步融合，不干涉高层策略。
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging
from backend.app.services.keyword_extractor import get_keyword_extractor
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class EvidenceHarvester:
    def __init__(self, vector_store: Any):
        self.vector_store = vector_store
        self.extractor = get_keyword_extractor()
        self.rrf_k = 60 # SOTA 推荐常数

    async def harvest(self, 
                      query: str, 
                      doc_id: Optional[str] = None, 
                      limit: int = 10,
                      toc_ranges: Optional[List[Tuple[int, int]]] = None) -> List[Dict]:
        """
        🚀 核心：证据收割主流程
        """
        print(f"🌊 [Harvester] 正在为查询执行 RRF 融合收割: {query[:settings.CONTEXT_COMMIT_QUERY_PREFIX]}...")

        # 1. 提取 Query 关键词 (逻辑标签碰撞源)
        query_tags = self.extractor.extract_keywords(query, top_n=10)
        
        # 2. 并行双路检索
        tasks = [
            self.vector_store.search(query, doc_id=doc_id, limit=limit * 3, page_ranges=toc_ranges),
            self.vector_store.search_by_tags(query_tags, doc_id=doc_id, limit=limit * 3, page_ranges=toc_ranges)
        ]
        
        vector_results, tag_results = await asyncio.gather(*tasks)
        
        # 3. 执行 RRF 排名融合
        all_hits = {}
        
        # 处理向量路径
        for rank, hit in enumerate(vector_results, 1):
            hit_id = hit["id"]
            if hit_id not in all_hits: all_hits[hit_id] = hit
            all_hits[hit_id]["rrf_score"] = all_hits[hit_id].get("rrf_score", 0.0) + (1.0 / (self.rrf_k + rank))
            all_hits[hit_id]["found_by_vector"] = True

        # 处理标签路径
        for rank, hit in enumerate(tag_results, 1):
            hit_id = hit["id"]
            if hit_id not in all_hits: all_hits[hit_id] = hit
            all_hits[hit_id]["rrf_score"] = all_hits[hit_id].get("rrf_score", 0.0) + (1.0 / (self.rrf_k + rank))
            all_hits[hit_id]["found_by_tags"] = True

        # 4. 物理偏置奖励 (ISR Boost)
        # 如果切片在 TOC 推荐的物理航道内，给予排名的位次提升（模拟奖励）
        if toc_ranges:
            for hit_id, hit in all_hits.items():
                p_num = hit.get("page_number", 0)
                in_range = any(s <= p_num <= e for s, e in toc_ranges)
                if in_range:
                    # 🚀 [V2.0] 位次奖励：相当于让其在合并名单中前移
                    hit["rrf_score"] += (1.0 / self.rrf_k) * 0.5 

        # 5. 排序并截断
        final_results = sorted(all_hits.values(), key=lambda x: x["rrf_score"], reverse=True)
        
        print(f"✅ [Harvester] 收割完成，RRF 融合候选数: {len(final_results)} -> 截断 Top-{limit}")
        return final_results[:limit]
