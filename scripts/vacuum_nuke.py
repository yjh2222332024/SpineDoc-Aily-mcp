import asyncio
from sqlmodel import text
from app.core.db import get_async_sessionmaker

async def vacuum_nuke():
    """
    SpineDoc 真空级清理工具
    职责：强行断开所有连接，级联抹除所有表数据并重置自增 ID。
    """
    session_maker = get_async_sessionmaker()
    print("🧨 [Vacuum-Nuke] 启动物理级数据抹除...")
    
    async with session_maker() as session:
        try:
            # 1. 级联抹除核心表 (CASCADE 会自动处理外键关联)
            # 2. 重置自增 ID (RESTART IDENTITY)
            sql = """
            TRUNCATE TABLE chunk, tocitem, document RESTART IDENTITY CASCADE;
            """
            await session.execute(text(sql))
            await session.commit()
            print("💥 [Success] 数据库已进入真空态：Chunk, TocItem, Document 已彻底清空并重置。")
        except Exception as e:
            await session.rollback()
            print(f"❌ [Error] 清理失败: {e}")

if __name__ == "__main__":
    asyncio.run(vacuum_nuke())
