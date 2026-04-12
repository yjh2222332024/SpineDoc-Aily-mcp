"""
SpineDoc 级联检索引擎 - V38.0 航道集群版
============================================
1. [Multi-Channel Fusion]：支持多达 5 个相关章节的联合航道检索。
2. [Range Fix]：彻底修复 physical_start > physical_end 的反向 Bug。
3. [Channel Merge]：自动合并连续页码，压榨 SQL 性能。
4. [Double Defense]：航道失败自动触发全局搜索，确保零漏检。
"""
from typing import List, Dict, Any, Optional, Tuple
from app.core.db import get_async_sessionmaker
from app.core.models import TocItem, Chunk
from sqlmodel import select
import numpy as np
import jieba
import logging

logger = logging.getLogger(__name__)

class CascadingRetriever:
    def __init__(self, router, reranker):
        self.router = router
        self.reranker = reranker
        self._session_maker = get_async_sessionmaker()

    def _merge_ranges(self, ranges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
        """
        🚀 架构师级：航道合并算法
        将重叠或相邻的页码范围合并，减少 SQL 负担，提升查询性能。
        """
        if not ranges: return []
        # 1. 修复反向并排序
        fixed_ranges = []
        for s, e in ranges:
            fixed_ranges.append((min(s, e), max(s, e)))
        fixed_ranges.sort()

        # 2. 合并逻辑
        merged = []
        curr_start, curr_end = fixed_ranges[0]

        for next_start, next_end in fixed_ranges[1:]:
            # 如果重叠或相邻（差距在 1 页以内），则合并
            if next_start <= curr_end + 1:
                curr_end = max(curr_end, next_end)
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = next_start, next_end
        merged.append((curr_start, curr_end))
        return merged

    async def retrieve(self, query: str, doc_id: Optional[str], vector_store: Any, 
                       limit: int = 5, **kwargs) -> List[Dict]:
        
        print(f"🌲 [Logic-Tree] 启动多航道集群筛选: {query[:30]}...")
        
        # 1. 第一层：TOC 语义撞击 (由 3 提升至 5，确保跨章节召回)
        raw_ranges = []
        toc_results = await vector_store.search_toc(query=query, doc_id=doc_id, limit=5)
        
        for t in toc_results:
            p_start = t.get('physical_start', 0)
            p_end = t.get('physical_end', 0)
            
            # 🚀 [V38.0 Fix] 修复反向范围 Bug：确保 p_start <= p_end
            if p_start > 0 and p_end > 0:
                s, e = min(p_start, p_end), max(p_start, p_end)
                print(f"  📍 锁定相关航道: {t.get('title')} (P{s} - P{e})")
                raw_ranges.append((s, e))

        # 2. 第二层：多航道融合与合并
        matched_ranges = self._merge_ranges(raw_ranges)
        if matched_ranges:
            print(f"  🔗 航道融合完成，合并为 {len(matched_ranges)} 个核心检索区间")

        # 3. 执行物理约束检索 (优先航道内召回)
        results = []
        if matched_ranges:
            # 🚀 [V38.0] 支持多航道联合检索 (Multi-Channel Search)
            results = await vector_store.search(query=query, doc_id=doc_id, limit=limit * 4, page_ranges=matched_ranges)
            print(f"  🌊 集群航道内共召回 {len(results)} 个候选分块")

        # 4. 兜底策略：如果航道内无匹配，切换至全局全量搜索
        if not results:
            print("  ⚠️ 航道内无直接匹配，切换至【全局全量搜索】最后一道防线...")
            results = await vector_store.search(query=query, doc_id=doc_id, limit=limit * 5)

        if not results: return []

        # 5. 第三层：语义权重蒸馏 (Pyramid Boost + JIT Keyword)
        # 预分词提高效率
        query_words = set(jieba.lcut(query))
        
        for r in results:
            if "content" not in r: r["content"] = r.get("text", "")
            if "page_number" not in r: r["page_number"] = r.get("page", 0)
            
            dist = r.get("_distance", 1.0)
            # 相似度归一化 (0-1)
            base_score = max(0.0, 1.0 - (float(dist) / 2.0))
            
            # [Iron Anchor Boost]：落在命中的集群航道范围内，权重显著加成
            r["_pyramid_boost"] = 1.0
            p_num = r["page_number"]
            for s, e in matched_ranges:
                if s <= p_num <= e:
                    r["_pyramid_boost"] = 3.5 # 航道内权重提升至 3.5 倍
                    break
            
            # [JIT Keyword Matching]：关键词重合度
            content_words = set(jieba.lcut(r["content"]))
            overlap = len(query_words & content_words) / len(query_words) if query_words else 0
            
            # 最终复合打分 = (向量分 + 关键词分 * 0.5) * Boost
            r["score"] = (base_score + overlap * 0.5) * r["_pyramid_boost"]

        # 6. 第四层：语义重排 (Reranker)
        # 先按 score 预筛选出 3 倍 limit 的内容送入精排
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        final_results = await self.reranker.rerank(query, results[:limit * 3], top_k=limit)
        
        # 统计平均置信度供调试
        if final_results:
            avg_conf = np.mean([x.get('score', 0) for x in final_results[:3]])
            print(f"⚖️ [Rerank] 精排完成，前三名平均置信度: {avg_conf:.2f}")
            
        return final_results
