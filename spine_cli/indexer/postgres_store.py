import asyncio
from typing import List, Dict, Optional
import httpx
from uuid import UUID
from sqlalchemy import text
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from backend.app.core.config import settings
from backend.app.core.db import get_async_sessionmaker, init_db
from backend.app.core.models import Chunk, Document

class PostgresStore:
    """
    SpineDoc 向量存储 (PostgreSQL + pgvector 版)
    【架构师级加固】：对接 SQLModel 体系，实现向量与元数据的一体化存储。
    """

    def __init__(self):
        self.is_available = True
        self.embedding_dim = settings.EMBEDDING_DIMENSION
        self._session_maker = get_async_sessionmaker()

    async def _ensure_initialized(self):
        """确保数据库和扩展已初始化"""
        await init_db()

    async def get_embeddings_api(self, texts: List[str]) -> List[List[float]]:
        """
        🚀 直接调用云端 Embedding API
        """
        BATCH_SIZE = 20
        all_embeddings = []

        async with httpx.AsyncClient(timeout=120.0) as client:
            headers = {
                "Authorization": f"Bearer {settings.EMBEDDING_API_KEY}",
                "Content-Type": "application/json"
            }
            
            for i in range(0, len(texts), BATCH_SIZE):
                batch_texts = texts[i:i + BATCH_SIZE]
                batch_texts = [t[:1500] for t in batch_texts]
                
                payload = {
                    "input": batch_texts,
                    "model": settings.EMBEDDING_MODEL_NAME
                }
                
                try:
                    resp = await client.post(
                        f"{settings.EMBEDDING_BASE_URL.rstrip('/')}/embeddings",
                        json=payload,
                        headers=headers
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    embeddings = [item["embedding"] for item in data["data"]]
                    all_embeddings.extend(embeddings)
                except Exception as e:
                    print(f"🚨 批量向量化异常 (Batch {i//BATCH_SIZE}): {e}")
                    all_embeddings.extend([[0.0] * self.embedding_dim] * len(batch_texts))
            
            return all_embeddings

    async def update_embedding(self, chunk_id: UUID, embedding: List[float]):
        """
        🚀 异步回填向量：用于流式入库后的高性能对齐。
        """
        async with self._session_maker() as session:
            stmt = text("UPDATE chunk SET embedding = :emb WHERE id = :cid")
            await session.execute(stmt, {"emb": str(embedding), "cid": chunk_id})
            await session.commit()

    async def add_documents(self, doc_id: str, chunks: List[Dict]):
        """
        将分块写入 PostgreSQL
        """
        # 1. 获取向量
        print(f"📡 调用 API 向量化: {len(chunks)} 个切片...")
        try:
            embeddings = await self.get_embeddings_api([c["content"] for c in chunks])
        except Exception as e:
            print(f"🚨 向量化失败: {e}")
            return

        # 2. 写入数据库
        async with self._session_maker() as session:
            # 找到对应的 Document UUID
            # 注意：doc_id 在 SpineEngine 中可能是 "doc_filename" 这种字符串
            # 我们需要确保它在数据库中存在，或者我们这里只管写入 Chunk
            # 如果 doc_id 不是 UUID，我们可能需要一个映射
            
            # 为了兼容性，我们假设 doc_id 是 Document 的 ID (UUID)
            # 如果不是，我们需要先查找或者创建一个 Document
            try:
                doc_uuid = UUID(doc_id)
            except ValueError:
                # 尝试通过 filename 查找
                stmt = select(Document).where(Document.filename == doc_id.replace("doc_", "") + ".pdf")
                result = await session.execute(stmt)
                db_doc = result.scalar_one_or_none()
                if not db_doc:
                    # 创建一个临时的 Document 记录 (如果需要)
                    db_doc = Document(id=UUID(int=hash(doc_id) & (2**128 - 1)), filename=doc_id)
                    session.add(db_doc)
                    await session.commit()
                    await session.refresh(db_doc)
                doc_uuid = db_doc.id

            db_chunks = []
            for i, c in enumerate(chunks):
                # 🆕 架构师修正：匹配 splitter 输出的 metadata_json
                meta = c.get("metadata_json", {})
                p_num = c.get("page_number") or meta.get("page_number") or 0
                
                db_chunk = Chunk(
                    content=c["content"],
                    page_number=int(p_num),
                    breadcrumb=str(c.get("breadcrumb", meta.get("breadcrumb", "未知章节"))),
                    embedding=embeddings[i],
                    document_id=doc_uuid,
                    metadata_json=meta
                )
                db_chunks.append(db_chunk)
            
            session.add_all(db_chunks)
            await session.commit()
            print(f"✅ [Postgres] 成功写入 {len(db_chunks)} 个语义切片 (ID: {doc_id})。")

    async def search_toc(self, query: str, doc_id: str, limit: int = 5) -> List[Dict]:
        """
        🚀 [V38.0] 双路混合目录检索 (Dual-Path TOC Search)
        同时对比标题向量和关键词聚合向量，锁定最强语义信号。
        """
        query_embeddings = await self.get_embeddings_api([query])
        query_vec = query_embeddings[0]

        async with self._session_maker() as session:
            vec_str = str(query_vec)
            # 🚀 V38.0: 引入 LEAST 函数，取标题距离和关键词距离的最小值
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
                "id": str(row[0]),
                "title": row[1],
                "physical_start": row[2],
                "physical_end": row[3],
                "level": row[4],
                "score": 1.0 - float(row[5]) if row[5] is not None else 0
            } for row in rows]
    async def search(self, query: str, doc_id: Optional[str] = None, limit: int = 5, page_ranges: Optional[List[tuple]] = None) -> List[Dict]:
        """
        ⚡ pgvector 驱动的向量搜索 (支持物理限域)
        """
        query_embeddings = await self.get_embeddings_api([query])
        query_vec = query_embeddings[0]
        
        async with self._session_maker() as session:
            vec_str = str(query_vec)
            sql = f"SELECT id, content, page_number, breadcrumb, embedding <=> '{vec_str}' as distance, metadata_json, document_id FROM chunk WHERE 1=1"
            
            if doc_id:
                sql += f" AND document_id = '{doc_id}'"
            
            if page_ranges:
                range_clauses = [f"(page_number >= {s} AND page_number <= {e})" for s, e in page_ranges]
                sql += f" AND ({' OR '.join(range_clauses)})"
            
            sql += f" ORDER BY distance LIMIT {limit}"
            
            result = await session.execute(text(sql))
            rows = result.fetchall()
            
            return [{
                "id": str(row[0]),
                "content": row[1],
                "page_number": row[2],
                "breadcrumb": row[3],
                "_distance": row[4],
                "metadata": row[5],
                "document_id": str(row[6])
            } for row in rows]
