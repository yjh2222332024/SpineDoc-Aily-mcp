
import asyncio
import sys
import argparse
from pathlib import Path

# 路径对齐
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.db import get_async_sessionmaker
from sqlmodel import select, delete
from app.core.models import Document, Chunk, TocItem

async def force_reset(filename: str):
    print(f"🚀 [Spine-Cleaner] 正在启动对 {filename} 的底层强制重置...")
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        # 1. 查找目标文档
        stmt = select(Document).where(Document.filename == filename)
        res = await session.execute(stmt)
        docs = res.scalars().all()
        
        if not docs:
            print(f"✨ 数据库中未发现 {filename}，无需重置。")
            return

        for doc in docs:
            print(f"🗑️ 正在抹除文档: {doc.filename} (ID: {doc.id})")
            # 2. 删除关联数据
            await session.execute(delete(Chunk).where(Chunk.document_id == doc.id))
            await session.execute(delete(TocItem).where(TocItem.document_id == doc.id))
            await session.execute(delete(Document).where(Document.id == doc.id))
            
        await session.commit()
        print(f"✅ 文档 {filename} 及其索引已彻底清空。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--filename", required=True, help="要重置的文档文件名")
    args = parser.parse_args()
    asyncio.run(force_reset(args.filename))
