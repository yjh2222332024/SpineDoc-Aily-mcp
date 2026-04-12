
import asyncio
import sys
from pathlib import Path

# 路径对齐
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.db import get_async_sessionmaker
from sqlmodel import select
from app.core.models import Document, TocItem

async def check_tocs():
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        # 获取 1.pdf 的所有 TOC
        stmt = select(Document).where(Document.filename == '1.pdf')
        doc = (await session.execute(stmt)).scalars().first()
        if not doc: 
            print("1.pdf not found")
            return
            
        print(f"📄 Document: {doc.filename} (ID: {doc.id})")
        toc_stmt = select(TocItem).where(TocItem.document_id == doc.id).order_by(TocItem.page.asc())
        items = (await session.execute(toc_stmt)).scalars().all()
        
        for it in items:
            print(f"  - Title: {it.title} | Page: {it.page} | Physical: {it.physical_start}")

if __name__ == "__main__":
    asyncio.run(check_tocs())
