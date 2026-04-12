"""
SpineDoc 数据库清理脚本
彻底删除 1.pdf 的所有残留，为 V8.0 全量入库腾出空间。
"""
import asyncio
from uuid import UUID
from sqlmodel import select, delete
from app.core.db import get_async_sessionmaker
from app.core.models import Document, TocItem, Chunk

async def reset():
    print("🧹 正在清理数据库中的 1.pdf 残余...")
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        # 1. 找到所有名为 1.pdf 的文档
        stmt = select(Document).where(Document.filename == "1.pdf")
        res = await session.execute(stmt)
        docs = res.scalars().all()
        
        if not docs:
            print("✅ 数据库已干净，无需清理。")
            return

        for doc in docs:
            print(f"🗑️ 正在删除文档 ID: {doc.id}")
            # 由于设置了 cascade delete，删除 document 会自动删除关联的 toc 和 chunk
            await session.delete(doc)
        
        await session.commit()
        print(f"🎉 清理完成，共删除 {len(docs)} 条历史记录。")

if __name__ == "__main__":
    asyncio.run(reset())
