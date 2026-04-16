"""
SpineDoc 向量存储服务 (VectorStore) - V48.6 架构回归版
======================================================
职责：作为 SpineDoc 知识库的物理守门员，提供向量检索、标签碰撞及 TOC 物理航道解析。
架构：回归 backend 核心服务层，实现逻辑主权统一。
"""

import asyncio
from typing import List, Dict, Optional, Tuple
import httpx
from uuid import UUID
from sqlalchemy import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.core.config import settings
from backend.app.core.db import get_async_sessionmaker, init_db
from backend.app.core.models import Chunk, Document, TocItem

class PostgresStore:
    def __init__(self):
        self.is_available = True
        self.embedding_dim = settings.EMBEDDING_DIMENSION
        self._session_maker = get_async_sessionmaker()

    async def _ensure_initialized(self):
        """确保数据库和扩展已初始化"""
        await init_db()

    async def get_embeddings_api(self, texts: List[str]) -> List[List[float]]:
        """直接调用云端 Embedding API"""
        BATCH_SIZE = 20
        all_embeddings = []
        async with httpx.AsyncClient(timeout=120.0) as client:
            headers = {"Authorization": f"Bearer {settings.EMBEDDING_API_KEY}", "Content-Type": "application/json"}
            for i in range(0, len(texts), BATCH_SIZE):
                batch_texts = [t[:settings.CONTEXT_VECTOR_BATCH_TEXT_PREFIX] for t in texts[i:i + BATCH_SIZE]]
                payload = {"input": batch_texts, "model": settings.EMBEDDING_MODEL_NAME}
                try:
                    resp = await client.post(f"{settings.EMBEDDING_BASE_URL.rstrip('/')}/embeddings", json=payload, headers=headers)
                    resp.raise_for_status()
                    embeddings = [item["embedding"] for item in resp.json()["data"]]
                    all_embeddings.extend(embeddings)
                except Exception as e:
                    print(f"🚨 批量向量化异常: {e}")
                    all_embeddings.extend([[0.0] * self.embedding_dim] * len(batch_texts))
            return all_embeddings

    async def search_toc(self, query: str, doc_id: str, limit: int = 5) -> List[Dict]:
        """🚀 双路混合目录检索 (Dual-Path TOC Search)"""
        query_embeddings = await self.get_embeddings_api([query])
        query_vec = query_embeddings[0]
        async with self._session_maker() as session:
            vec_str = str(query_vec)
            sql = f"""
            SELECT id, title, physical_start, physical_end, level, 
                   LEAST(embedding <=> '{vec_str}', keyword_embedding <=> '{vec_str}') as distance
            FROM tocitem
            WHERE document_id = '{doc_id}' AND embedding IS NOT NULL
            ORDER BY distance LIMIT {limit}
            """
            result = await session.execute(text(sql))
            rows = result.fetchall()
            return [{
                "id": str(row[0]), "title": row[1], "physical_start": row[2], 
                "physical_end": row[3], "level": row[4], "score": 1.0 - float(row[5]) if row[5] is not None else 0
            } for row in rows]

    async def search(self, query: str, doc_id: Optional[str] = None, limit: int = 5, page_ranges: Optional[List[tuple]] = None) -> List[Dict]:
        """⚡ pgvector 驱动的向量搜索"""
        query_embeddings = await self.get_embeddings_api([query])
        query_vec = query_embeddings[0]
        async with self._session_maker() as session:
            vec_str = str(query_vec)
            # 🚀 [V3.5] 确权补全：向量搜索也必须携带 logic_tags，确保全链路契约一致
            sql = "SELECT id, content, page_number, breadcrumb, logic_tags, embedding <=> :vec as distance, document_id FROM chunk WHERE 1=1"
            if doc_id: sql += " AND document_id = :doc_id"
            if page_ranges:
                range_clauses = [f"(page_number >= {s} AND page_number <= {e})" for s, e in page_ranges]
                sql += f" AND ({' OR '.join(range_clauses)})"
            sql += " ORDER BY distance LIMIT :limit"
            result = await session.execute(text(sql), {"vec": vec_str, "doc_id": doc_id, "limit": limit})
            rows = result.fetchall()
            return [{"id": str(row[0]), "content": row[1], "page_number": row[2], "breadcrumb": row[3], "logic_tags": row[4], "_distance": row[5], "document_id": str(row[6])} for row in rows]

    async def search_by_tags(self, tags: List[str], doc_id: Optional[str] = None, limit: int = 20, page_ranges: Optional[List[tuple]] = None) -> List[Dict]:
        """🚀 [V48.5] 标签确权检索"""
        if not tags: return []
        async with self._session_maker() as session:
            sql = "SELECT id, content, page_number, breadcrumb, logic_tags, document_id FROM chunk WHERE 1=1"
            if doc_id: sql += " AND document_id = :doc_id"
            sql += " AND logic_tags ?| :tags"
            if page_ranges:
                range_clauses = [f"(page_number >= {s} AND page_number <= {e})" for s, e in page_ranges]
                sql += f" AND ({' OR '.join(range_clauses)})"
            sql += " LIMIT :limit"
            result = await session.execute(text(sql), {"tags": tags, "doc_id": doc_id, "limit": limit})
            rows = result.fetchall()
            return [{"id": str(row[0]), "content": row[1], "page_number": row[2], "breadcrumb": row[3], "logic_tags": row[4], "document_id": str(row[5]), "found_by_tags": True} for row in rows]

    async def get_toc_ranges_by_ids(self, toc_ids: List[UUID]) -> List[Tuple[int, int]]:
        """🚀 [V48.6] 3.0 原子工具：解析 TOC ID 集合为物理航道"""
        if not toc_ids: return []
        async with self._session_maker() as session:
            stmt = select(TocItem.physical_start, TocItem.physical_end).where(TocItem.id.in_(toc_ids))
            result = await session.execute(stmt)
            rows = result.all()
            return [(int(r[0]), int(r[1])) for r in rows] if rows else []

    async def is_lane_active(self, doc_id: str, p_start: int, p_end: int) -> bool:
        """
        🚀 [V49.2] 活性探测：物理核验区间内是否有真实分片。
        """
        async with self._session_maker() as session:
            # 采用极速 COUNT(1) 探测
            sql = "SELECT 1 FROM chunk WHERE document_id = :doc_id AND page_number >= :s AND page_number <= :e LIMIT 1"
            result = await session.execute(text(sql), {"doc_id": doc_id, "s": p_start, "e": p_end})
            return result.scalar() is not None
