"""
AilyHarvester
=============
Responsibility: Decouple local compute, using Aily for semantic matching and Bitable tags for mixed recall.
Architecture: Integrated with the RRF ranking fusion principles from VectorEvidenceSearcher.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
import logging
from backend.app.services.feishu.aily_bridge import aily_bridge
from backend.app.services.keyword_extractor import get_keyword_extractor
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class AilyHarvester:
    """
    AilyHarvester: Core component for Feishu ecosystem integration.
    """
    def __init__(self, store=None):
        from backend.app.services.feishu.bitable_ledger import bitable_ledger
        self.extractor = get_keyword_extractor()
        self.store = store or bitable_ledger
        self.rrf_k = 60
        self.W_AILY = 0.6
        self.W_TAGS = 0.3

    async def harvest(self, 
                      query: str, 
                      doc_record_id: Optional[str] = None, 
                      limit: int = 10) -> List[Dict]:
        """
        🚀 核心逻辑：标准双路并行 RRF 融合 (Aily Vector=0.6, Bitable Tags=0.3)
        """
        print(f"📡 [AilyHarvester] 启动双路并行收割: {query[:20]}...")

        # 1. 提取关键词
        query_tags = self.extractor.extract_keywords(query, top_n=5)
        
        # 2. 【并行质询】
        tasks = [
            aily_bridge.ask_knowledge(query),
            self.store.search_chunks(query, doc_record_id=doc_record_id, tags=query_tags, limit=limit * 2)
        ]
        vector_results, tag_results = await asyncio.gather(*tasks)
        
        # 3. 【排名熔炼】
        fused_scores = {} # Dict[str, float]
        id_to_data = {}   # Data Store
        
        # --- 路径 A: Aily Vector (0.6) ---
        for rank, hit in enumerate(vector_results, 1):
            rid = hit.get("id")
            if not rid: continue
            
            score = self.W_AILY / (self.rrf_k + rank)
            fused_scores[rid] = fused_scores.get(rid, 0.0) + score
            id_to_data[rid] = hit
            id_to_data[rid]["found_by_aily"] = True

        # --- 路径 B: Bitable Tags (0.3) ---
        for rank, hit in enumerate(tag_results, 1):
            rid = hit.get("id")
            if not rid: continue
            
            score = self.W_TAGS / (self.rrf_k + rank)
            fused_scores[rid] = fused_scores.get(rid, 0.0) + score
            
            if rid not in id_to_data: id_to_data[rid] = hit
            id_to_data[rid]["found_by_tags"] = True

        # 4. 【排序截断】
        final_list = []
        for rid, total_score in fused_scores.items():
            item = id_to_data[rid]
            item["rrf_score"] = total_score
            final_list.append(item)
            
        final_list.sort(key=lambda x: x["rrf_score"], reverse=True)
        
        print(f"✅ [AilyHarvester] RRF 融合完成。召回 unique 证据: {len(final_list)}")
        return final_list[:limit]




aily_harvester = AilyHarvester()
