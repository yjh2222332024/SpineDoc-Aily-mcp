"""
⚠️ DEPRECATED - SpineDoc 金字塔收割机 (PyramidHarvester)
===============================================
职责：此模块已废弃。三段式检索已简化为 AilyHarvester 的云端直接收割。
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
import logging
from backend.app.services.rag.vector_store import PostgresStore
from backend.app.services.keyword_extractor import get_keyword_extractor
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class PyramidHarvester:
    def __init__(self, vector_store: PostgresStore):
        self.store = vector_store
        self.extractor = get_keyword_extractor()
        self.rrf_k = 60

    async def harvest(self, 
                      query: str, 
                      doc_id: str, 
                      limit: int = 10) -> List[Dict]:
        """
        🚀 [V49.2] 金字塔巡航流程
        """
        print(f"🌲 [Pyramid] 启动逻辑巡航: {query[:settings.CONTEXT_COMMIT_QUERY_PREFIX]}...")

        # --- Step 1: 逻辑预瞄 (TOC Probing) ---
        # 探测最相关的 5 个章节
        toc_hits = await self.store.search_toc(query, doc_id, limit=5)
        
        # 动态活性过滤
        lane_ranges = []
        for t in toc_hits:
            p_start, p_end = t['physical_start'], t['physical_end']
            
            # 🚀 [V49.2] 物理活性探测：不再假设层级，直接去数据库看有没有货
            is_active = await self.store.is_lane_active(doc_id, p_start, p_end)
            
            if is_active:
                lane_ranges.append((p_start, p_end))
                print(f"  📍 锁定有效航道: {t['title']} (P{p_start}-P{p_end})")
            else:
                print(f"  ⏩ [Pruning] 剔除空壳章节: {t['title']} (P{p_start}-P{p_end})")

        # --- Step 2: 语义指纹提取 ---
        query_tags = self.extractor.extract_keywords(query, top_n=10)

        # --- Step 3: 多路并行收割 ---
        tasks = [
            self.store.search(query, doc_id=doc_id, limit=limit * 3, page_ranges=lane_ranges if lane_ranges else None),
            self.store.search_by_tags(query_tags, doc_id=doc_id, limit=limit * 3, page_ranges=lane_ranges if lane_ranges else None),
            self.store.search(query, doc_id=doc_id, limit=limit) # 全局兜底
        ]
        
        vec_hits, tag_hits, global_vec_hits = await asyncio.gather(*tasks)

        # --- Step 4: RRF 排名融合 ---
        all_hits = {}
        
        def update_rrf(hits, weight=1.0, signal_name="vec"):
            for rank, hit in enumerate(hits, 1):
                h_id = hit["id"]
                if h_id not in all_hits: all_hits[h_id] = hit
                score = (1.0 / (self.rrf_k + rank)) * weight
                all_hits[h_id]["rrf_score"] = all_hits[h_id].get("rrf_score", 0.0) + score
                all_hits[h_id][f"found_by_{signal_name}"] = True

        update_rrf(vec_hits, weight=1.2, signal_name="lane_vec")
        update_rrf(tag_hits, weight=1.5, signal_name="lane_tag") 
        update_rrf(global_vec_hits, weight=0.8, signal_name="global_vec")

        # --- Step 5: 物理航道与路径感知二次加成 ---
        final_list = []
        for hit in all_hits.values():
            p_num = hit.get("page_number", 0)
            breadcrumb = str(hit.get("breadcrumb", ""))
            
            # 物理航道加权
            for s, e in lane_ranges:
                if s <= p_num <= e:
                    hit["rrf_score"] *= 1.2
                    hit["in_pyramid_lane"] = True
                    break
            
            # 路径感知加权：如果 breadcrumb 包含了关键词
            match_count = sum(1 for kw in query_tags if kw.lower() in breadcrumb.lower())
            if match_count > 0:
                hit["rrf_score"] *= (1.0 + 0.1 * match_count)
                hit["path_aware"] = True

            final_list.append(hit)

        final_list.sort(key=lambda x: x["rrf_score"], reverse=True)
        
        print(f"✅ [Pyramid] 收割完成，RRF 融合候选: {len(final_list)} -> Top-{limit}")
        return final_list[:limit]
