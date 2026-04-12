import asyncio
import sys
from pathlib import Path

# 修正路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem
from sqlalchemy import select

async def inspect():
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        # 获取最新文档
        docs = (await session.execute(select(Document).order_by(Document.created_at.desc()))).scalars().all()
        if not docs:
            print("❌ 数据库里没文档啊！")
            return
        
        doc = docs[0]
        print(f"📄 文档: {doc.filename} (ID: {doc.id})")
        
        # 获取所有 TOC 项
        tocs = (await session.execute(
            select(TocItem).where(TocItem.document_id == doc.id).order_by(TocItem.physical_start)
        )).scalars().all()
        
        print(f"{'Title':<30} | {'Level':<5} | {'Physical':<15}")
        print("-" * 55)
        for t in tocs:
            print(f"{t.title[:30]:<30} | {t.level:<5} | {t.physical_start}-{t.physical_end}")

if __name__ == "__main__":
    asyncio.run(inspect())
