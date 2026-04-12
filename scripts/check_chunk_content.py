
import asyncio
import sys
from pathlib import Path

# 路径对齐
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.db import get_async_sessionmaker
from sqlmodel import select
from app.core.models import Chunk, Document

async def check_chunks():
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        stmt = select(Chunk).limit(5)
        result = await session.execute(stmt)
        chunks = result.scalars().all()
        
        print(f"✅ 抽样检查 {len(chunks)} 个分块:")
        for c in chunks:
            print(f"Chunk ID: {c.id} | Doc ID: {c.document_id} | Page: {c.page_number}")
            if c.document_id:
                doc = await session.get(Document, c.document_id)
                print(f"  -> 所属文档: {doc.filename if doc else 'NotFound'}")
            else:
                print("  -> ❌ document_id 为空")

if __name__ == "__main__":
    asyncio.run(check_chunks())
