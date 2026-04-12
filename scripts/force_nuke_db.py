
import asyncio
import sys
from pathlib import Path

# 路径对齐
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.db import get_async_sessionmaker
from sqlmodel import delete
from app.core.models import Document, Chunk, TocItem

async def nuke():
    print("🧨 [Spine-Nuke] 正在执行全库物理抹除...")
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        # 直接暴力清空三张核心表
        await session.execute(delete(Chunk))
        await session.execute(delete(TocItem))
        await session.execute(delete(Document))
        await session.commit()
        print("💥 数据库已推平：Chunk, TocItem, Document 记录已全部清零。")

if __name__ == "__main__":
    asyncio.run(nuke())
