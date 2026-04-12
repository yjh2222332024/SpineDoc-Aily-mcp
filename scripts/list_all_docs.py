"""
检查数据库中所有文档
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.db import get_async_sessionmaker
from sqlmodel import select
from app.core.models import Document, TocItem, Chunk

async def list_all_documents():
    session_maker = get_async_sessionmaker()
    
    async with session_maker() as session:
        # 1. 查找所有文档
        stmt = select(Document).order_by(Document.created_at.desc())
        docs = (await session.execute(stmt)).scalars().all()
        
        if not docs:
            print("❌ 数据库中没有文档")
            return
        
        print("=" * 80)
        print(f"📚 数据库中共有 {len(docs)} 个文档")
        print("=" * 80)
        
        for i, doc in enumerate(docs):
            print(f"\n📄 [{i+1}] {doc.filename}")
            print(f"   ID: {doc.id}")
            print(f"   总页数：{doc.total_pages}")
            print(f"   is_scanned: {doc.is_scanned}")
            print(f"   page_offset: {doc.page_offset}")
            print(f"   状态：{doc.status}")
            print(f"   创建时间：{doc.created_at}")
            
            # 统计 TOC 和 Chunk
            stmt_toc = select(TocItem).where(TocItem.document_id == doc.id)
            toc_count = len((await session.execute(stmt_toc)).scalars().all())
            
            stmt_chunk = select(Chunk).where(Chunk.document_id == doc.id)
            chunk_count = len((await session.execute(stmt_chunk)).scalars().all())
            
            print(f"   TOC 数量：{toc_count}")
            print(f"   Chunk 数量：{chunk_count}")
            
            # 检查内容质量
            if chunk_count > 0:
                chunks = (await session.execute(stmt_chunk)).scalars().all()
                empty_chunks = sum(1 for c in chunks if "[Content pending patch]" in c.content)
                has_real_content = chunk_count - empty_chunks
                print(f"   有真实内容：{has_real_content}/{chunk_count} ({has_real_content/chunk_count*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(list_all_documents())
