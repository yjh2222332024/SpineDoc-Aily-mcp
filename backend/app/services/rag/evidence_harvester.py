"""
VectorEvidenceSearcher
=====================
Responsibility: Use RRF (Reciprocal Rank Fusion) algorithm to integrate vector search, 
tag matching, and TOC priors to provide high-performance, deterministic evidence streams.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import logging
from backend.app.services.keyword_extractor import get_keyword_extractor
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class VectorEvidenceSearcher:
    def __init__(self, vector_store: Any):
        self.vector_store = vector_store
        self.extractor = get_keyword_extractor()
        self.rrf_k = 60 # Standard constant for RRF

    async def harvest(self, 
                      query: str, 
                      doc_id: Optional[str] = None, 
                      limit: int = 10,
                      toc_ranges: Optional[List[Tuple[int, int]]] = None) -> List[Dict]:
        """
        Main evidence search process using RRF.
        """
        print(f"[VectorEvidenceSearcher] Executing RRF fusion search for: {query[:settings.CONTEXT_COMMIT_QUERY_PREFIX]}...")

        # 1. Extract Query Keywords
        query_tags = self.extractor.extract_keywords(query, top_n=10)

        # 2. Parallel dual-path search
        tasks = [
            self.vector_store.search(query, doc_id=doc_id, limit=limit * 3, page_ranges=toc_ranges),
            self.vector_store.search_by_tags(query_tags, doc_id=doc_id, limit=limit * 3, page_ranges=toc_ranges)
        ]

        vector_results, tag_results = await asyncio.gather(*tasks)

        # 3. Reciprocal Rank Fusion
        all_hits = {}

        # Process vector path
        for rank, hit in enumerate(vector_results, 1):
            hit_id = hit["id"]
            if hit_id not in all_hits: all_hits[hit_id] = hit
            all_hits[hit_id]["rrf_score"] = all_hits[hit_id].get("rrf_score", 0.0) + (1.0 / (self.rrf_k + rank))
            all_hits[hit_id]["found_by_vector"] = True

        # Process tag path
        for rank, hit in enumerate(tag_results, 1):
            hit_id = hit["id"]
            if hit_id not in all_hits: all_hits[hit_id] = hit
            all_hits[hit_id]["rrf_score"] = all_hits[hit_id].get("rrf_score", 0.0) + (1.0 / (self.rrf_k + rank))
            all_hits[hit_id]["found_by_tags"] = True

        # 4. Physical Bias Boost
        if toc_ranges:
            for hit_id, hit in all_hits.items():
                p_num = hit.get("page_number", 0)
                in_range = any(s <= p_num <= e for s, e in toc_ranges)
                if in_range:
                    hit["rrf_score"] += (1.0 / self.rrf_k) * 0.5 

        # 5. Sort and truncate
        final_results = sorted(all_hits.values(), key=lambda x: x["rrf_score"], reverse=True)

        print(f"✅ [VectorEvidenceSearcher] Search completed, candidates found: {len(final_results)} -> Top-{limit}")
        return final_results[:limit]

