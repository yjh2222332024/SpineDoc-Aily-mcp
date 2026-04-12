"""
测试向量检索的实际效果
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from spine_cli.core.engine import SpineEngine
from spine_cli.indexer.postgres_store import PostgresStore
from app.core.db import get_async_sessionmaker
from sqlmodel import select
from app.core.models import Document

async def test_retrieval():
    engine = SpineEngine()
    
    # 获取文档
    docs = await engine.list_documents()
    if not docs:
        print("❌ 没有文档")
        return
    
    doc = docs[0]
    doc_id = doc["id"]
    print(f"使用文档：{doc['filename']} (ID: {doc_id})")
    
    # 测试查询
    query = "SM4 ZUC 国际标准化"
    print(f"\n🔍 测试查询：{query}")
    
    # 获取文档路径
    doc_detail = await engine.get_document(doc_id)
    doc["path"] = doc_detail["path"]
    
    # 1. 直接调用向量检索
    print("\n=== 测试 1: 原始向量检索 (limit=30) ===")
    results = await engine.cascading_retriever.retrieve(
        query=query,
        doc_id=doc_id,
        vector_store=engine.vector_store,
        document=doc,
        limit=30
    )
    
    print(f"返回 {len(results)} 个结果")
    for i, r in enumerate(results[:10]):
        content_preview = r.get('content', r.get('text', ''))[:150].replace('\n', ' ')
        print(f"\n[{i+1}] Page {r.get('page', 'N/A')} - {r.get('breadcrumb', 'N/A')}")
        print(f"    内容：{content_preview}...")
        
        # 检查是否包含关键词
        has_sm4 = "SM4" in content_preview
        has_zuc = "ZUC" in content_preview
        has_iso = "ISO" in content_preview or "国际" in content_preview
        print(f"    关键词：SM4={has_sm4}, ZUC={has_zuc}, 国际={has_iso}")
    
    # 2. 手动 SQL 查询包含 SM4 的 Chunk
    print("\n=== 测试 2: 直接 SQL 查询包含 SM4 的 Chunk ===")
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        stmt = select(Chunk).where(
            Chunk.document_id == doc_id,
            Chunk.content.contains("SM4")
        ).limit(5)
        chunks = (await session.execute(stmt)).scalars().all()
        
        for i, c in enumerate(chunks):
            print(f"\n[SQL-{i+1}] Page {c.page_number} - {c.breadcrumb}")
            print(f"    内容：{c.content[:200].replace(chr(10), ' ')}...")

if __name__ == "__main__":
    from app.core.models import Chunk
    asyncio.run(test_retrieval())
