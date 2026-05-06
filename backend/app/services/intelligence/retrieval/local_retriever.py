"""
LocalRetriever - Multi-Stage Expert Router (MoE-LMLR)
=====================================================
Responsibility:
1. Physical Expert: Scan Bitable metadata (filenames, tags).
2. Galaxy Expert: Vector collision with Galaxy centroids.
3. Decision Gating: Lock semantic territories before harvesting.

替代旧名称：SovereignSentry
"""

import json
import logging
import asyncio
import os
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from backend.app.services.feishu.bitable_ledger import bitable_ledger
from backend.app.services.ingestion.embedding import embedding_service
from .constants import (
    SIMILARITY_THRESHOLD,
    PYRAMID_FALLBACK_THRESHOLD,
    VECTOR_SIMILARITY_THRESHOLD,
    DIRECT_NAME_MATCH_SCORE,
    KEYWORD_MATCH_SCORE,
    PRECISION_SAMPLE_LIMIT,
    SINGLE_DOC_STABILITY,
    SINGLE_DOC_CONFIDENCE,
)

logger = logging.getLogger(__name__)

class LocalRetriever:
    """
     [V150.0] 本地检索器：金字塔重排检索。
    替代旧名称：SovereignSentry
    """
    def __init__(self):
        self.similarity_threshold = SIMILARITY_THRESHOLD

    async def route_query(self, query: str, limit: int = 3, pre_located_galaxies: List[Dict] = None) -> List[Dict[str, Any]]:
        """
         [V150.0] 主权哨兵：金字塔重排检索
        逻辑：星系撞击 -> 领地收割 -> 云端重排 -> 金字塔回退

        Args:
            pre_located_galaxies: 预定位的星系列表，跳过重复定位
        """
        from backend.app.services.ingestion.zhipu_reranker import zhipu_reranker

        print(f" [SovereignSentry] 哨兵就位，开始主权质询: {query[:30]}...")

        # 1. 物理专家与星系专家：锁定主权领地（如果有预定位则跳过）
        if pre_located_galaxies:
            # pre_located_galaxies 可能是 List[Dict] (territory objects) 或 List[str] (galaxy IDs)
            if pre_located_galaxies and isinstance(pre_located_galaxies[0], str):
                # 是 galaxy ID 列表，需要转换为 territory 格式
                locked_territories = [{"source_id": gid, "source_name": "Pre-located"} for gid in pre_located_galaxies]
            else:
                locked_territories = pre_located_galaxies
            print(f" [SemanticExpert] 复用预定位领地 {len(locked_territories)} 个")
        else:
            physical_hits = await self._physical_expert(query)
            galaxy_hits = await self._galaxy_expert(query)
            locked_territories = self._gate_decision(physical_hits, galaxy_hits)
        
        if not locked_territories:
            print(" [SovereignSentry] 撞击微弱，主权定位失败。")
            return []

        # 2. 语义专家：主权领地收割
        galaxy_ids = [t["source_id"] for t in locked_territories]
        print(f" [SemanticExpert] 正在领地 {', '.join([t['source_name'] for t in locked_territories])} 内执行物理采样...")
        
        # 利用 V150.0 的反向收割逻辑，直接拉取分片内容
        candidates = await bitable_ledger.search_chunks(
            galaxy_ids=galaxy_ids,
            limit=PRECISION_SAMPLE_LIMIT  # 精准采样
        )
        
        if not candidates:
            print(" [SemanticExpert] 领地内未发现原始证据。")
            return []

        # 3. 云端质证：语义重排 (Rerank)
        candidate_texts = [c.get("content", "") for c in candidates]
        print(f"🧠 [CloudRerank] 正在质询智谱云端，对 {len(candidate_texts)} 条分片执行重排...")
        
        rerank_results = await zhipu_reranker.rerank(query, candidate_texts)
        
        # 4. 逻辑裁定：映射重排得分并执行金字塔红线校验
        scored_chunks = []
        for res in rerank_results:
            idx = res.get("index")
            score = res.get("relevance_score", 0.0)
            if idx is not None and idx < len(candidates):
                chunk = candidates[idx]
                chunk["score"] = score
                scored_chunks.append(chunk)

        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        top_score = scored_chunks[0]["score"] if scored_chunks else 0.0
        
        #  [金字塔回退] 如果细节分片得分不足，上浮到星系共识摘要 (Level 1)
        if top_score < PYRAMID_FALLBACK_THRESHOLD:
            print(f"🔼 [PyramidFallback] 细节匹配度过低 ({top_score:.2f})，正在上浮至星系共识层...")
            # 搜索该星系内的 L1 节点 (Level=1)
            # 注意：此处的 search_chunks 逻辑需支持 Level 过滤或通过坐标匹配
            consensus_chunks = await self._fetch_galaxy_consensus(galaxy_ids)
            if consensus_chunks:
                print(f" [PyramidFallback] 已锁定 {len(consensus_chunks)} 条星系级共识。")
                return consensus_chunks[:limit]

        final_evidence = scored_chunks[:limit]
        print(f"🏁 [SovereignSentry] 质询结束，锁定 {len(final_evidence)} 条高精度细节证据。")
        return final_evidence

    async def route_query_by_document(self, doc_id: str, query: str, limit: int = 5) -> List[Dict]:
        """ [V220.0] 单文档直路：跳过星系定位，在目标文档分片内直接语义重排。"""
        if not doc_id or doc_id == "all":
            return []

        from backend.app.services.ingestion.zhipu_reranker import zhipu_reranker

        print(f" [SovereignSentry] 单文档直路 | doc_id={doc_id[:8]}... | query={query[:30]}...")

        candidates = await bitable_ledger.fetch_chunks_by_document(doc_id, limit=15)
        if not candidates:
            print(" [SovereignSentry] 文档内未发现分片。")
            return []

        candidate_texts = [c.get("content", "") for c in candidates]
        rerank_results = await zhipu_reranker.rerank(query, candidate_texts)

        scored = []
        for res in rerank_results:
            idx = res.get("index")
            score = res.get("relevance_score", 0.0)
            if idx is not None and idx < len(candidates):
                chunk = candidates[idx]
                chunk["score"] = score
                scored.append(chunk)

        scored.sort(key=lambda x: x["score"], reverse=True)
        final = scored[:limit]

        for e in final:
            e["claims"] = [e.get("summary", e.get("content", ""))]
            e["stability"] = SINGLE_DOC_STABILITY
            e["origin"] = "LOCAL_GALAXY"
            e["is_sovereign"] = True
            e["color"] = "GREEN"
            e["confidence"] = SINGLE_DOC_CONFIDENCE

        print(f"🏁 [SovereignSentry] 单文档收割完成，锁定 {len(final)} 条证据。")
        return final

    async def pre_locate_galaxies(self, query: str) -> List[Dict]:
        """ [Dedupe] 预先定位星系，返回锁定领土列表"""
        physical_hits = await self._physical_expert(query)
        galaxy_hits = await self._galaxy_expert(query)
        locked = self._gate_decision(physical_hits, galaxy_hits)
        return locked

    async def _fetch_galaxy_consensus(self, galaxy_ids: List[str]) -> List[Dict]:
        """
        物理确权：专门拉取星系的 Level 1 共识分片
        """
        # 这里的逻辑通过 logic_coord 为 'L1-' 开头来识别
        # 实际更稳健的做法是直接在 Galaxies 表里读取摘要字段
        results = []
        for gid in galaxy_ids:
            # 这里的逻辑与 search_chunks 类似，但可以更定向
            # 为了丝滑，我们直接复用 search_chunks 的全量扫描，然后在内存中筛 L1
            all_chunks = await bitable_ledger.search_chunks(galaxy_ids=[gid], limit=10)
            # 假设 L1 节点在入库时设置了 logic_coord="L1-..."
            l1_nodes = [c for c in all_chunks if c.get("id", "").startswith("L1") or "共识" in c.get("content", "")]
            results.extend(l1_nodes)
        return results

    async def _physical_expert(self, query: str) -> List[Dict]:
        """
        物理专家：关键词匹配星系名称和锚点关键词，作为向量碰撞的兜底。
        """
        galaxies = await self._fetch_all_galaxy_metadata()
        if not galaxies:
            return []

        query_lower = query.lower()
        query_words = [w for w in query_lower.split() if len(w) > 1]

        hits = []
        for g in galaxies:
            name = g.get("name", "").lower()
            keywords = g.get("keywords", "").lower()

            # 星系名称直接匹配
            if query_lower in name or any(w in name for w in query_words):
                hits.append({"id": g["id"], "name": g["name"], "score": DIRECT_NAME_MATCH_SCORE})
                continue

            # 锚点关键词匹配
            if keywords and (query_lower in keywords or any(w in keywords for w in query_words)):
                hits.append({"id": g["id"], "name": g["name"], "score": KEYWORD_MATCH_SCORE})

        return hits

    async def _fetch_all_galaxy_metadata(self) -> List[Dict]:
        """获取所有星系的元数据（名称、锚点关键词），不含向量"""
        gal_table = bitable_ledger.tables['galaxies']['id']
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{bitable_ledger.app_token}/tables/{gal_table}/records"
        resp = await bitable_ledger._api_request("GET", url)
        items = resp.get("data", {}).get("items", [])

        results = []
        for it in items:
            f = it.get("fields", {})
            results.append({
                "id": it["record_id"],
                "name": f.get("星系名称", "Unknown"),
                "keywords": f.get("锚点关键词", ""),
            })
        return results

    async def _galaxy_expert(self, query: str) -> List[Dict]:
        """
        星系专家：Query Vector vs Galaxy Centroids
        """
        #  [V110.1] 修复接口调用：EmbeddingService 使用 get_embeddings (复数)
        embeddings = await embedding_service.get_embeddings([query])
        if not embeddings: return []
        query_vector = embeddings[0]

        galaxies = await self._fetch_all_galaxy_centroids()
        if not galaxies: return []

        v1 = np.array(query_vector)
        impact_results = []
        
        for g in galaxies:
            v2 = g["centroid"]
            if len(v1) != len(v2): continue
            
            # 余弦相似度
            score = float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
            if score > VECTOR_SIMILARITY_THRESHOLD:  # 哨兵的第一道门槛
                impact_results.append({
                    "id": g["id"],
                    "name": g["name"],
                    "score": score
                })
        
        impact_results.sort(key=lambda x: x["score"], reverse=True)
        return impact_results

    def _gate_decision(self, phys_hits: List[Dict], gal_hits: List[Dict]) -> List[Dict]:
        """
        门控裁定：综合物理命中与星系撞击结果。
        优先向量碰撞，无结果时用关键词匹配兜底。
        """
        # 优先使用星系撞击（语义匹配）
        if gal_hits:
            results = []
            for g in gal_hits:
                results.append({
                    "doc_id": g["id"],
                    "source_id": g["id"],
                    "source_name": g["name"],
                    "relevance": True,
                    "score": g["score"],
                    "type": "GALAXY"
                })
            return results

        # 兜底：使用物理匹配（关键词）
        if phys_hits:
            results = []
            for p in phys_hits:
                results.append({
                    "doc_id": p["id"],
                    "source_id": p["id"],
                    "source_name": p["name"],
                    "relevance": True,
                    "score": p["score"],
                    "type": "PHYSICAL"
                })
            return results

        return []

    async def _fetch_all_galaxy_centroids(self) -> List[Dict]:
        """从 Bitable 获取所有星系重心"""
        gal_table = bitable_ledger.tables['galaxies']['id']
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{bitable_ledger.app_token}/tables/{gal_table}/records"
        resp = await bitable_ledger._api_request("GET", url)
        items = resp.get("data", {}).get("items", [])
        
        results = []
        for it in items:
            f = it.get("fields", {})
            vec_str = f.get("重心向量", "[]")
            try:
                vec = np.array(json.loads(vec_str)) if isinstance(vec_str, str) else np.array(vec_str)
                results.append({
                    "id": it["record_id"],
                    "name": f.get("星系名称", "Unknown"),
                    "centroid": vec
                })
            except: continue
        return results


# 向后兼容别名
SovereignSentry = LocalRetriever
