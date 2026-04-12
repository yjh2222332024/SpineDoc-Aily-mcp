
import asyncio
import sys
from pathlib import Path

# 路径对齐
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from spine_cli.indexer.postgres_store import PostgresStore
from app.core.db import get_async_sessionmaker
from sqlmodel import select
from app.core.models import Document

async def debug_retrieval():
    store = PostgresStore()
    query = "经典的密码学安全性定义"
    print(f"🔍 正在测试全局向量检索，Query: {query}")
    
    hits = await store.search(query=query, limit=20)
    
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        for i, h in enumerate(hits):
            doc_id = h.get("document_id")
            doc = await session.get(Document, doc_id)
            fname = doc.filename if doc else "Unknown"
            print(f"[{i+1}] {fname} (P{h.get('page_number')}) | Distance: {h.get('_distance', 0):.4f}")
            print(f"    Content: {h.get('content', '')[:150]}...")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(debug_retrieval())
