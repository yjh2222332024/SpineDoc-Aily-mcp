"""
🚀 SpineDoc 数据库清空工具 - Silent Nuke
=======================================
功能：直接执行 SQL 清空所有表，无需确认
"""
import asyncio
import sys
from pathlib import Path

# 路径对齐
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.db import get_async_sessionmaker, init_db
from sqlalchemy import text

async def silent_nuke():
    print("🚀 [Silent Nuke] 正在执行数据库清空...")
    
    await init_db()
    session_maker = get_async_sessionmaker()
    
    async with session_maker() as session:
        try:
            # 使用原生 SQL 清空（绕过外键约束）
            print("🗑️  删除所有 Chunk...")
            await session.execute(text("TRUNCATE TABLE chunk CASCADE"))
            
            print("🗑️  删除所有 TOC 项...")
            await session.execute(text("TRUNCATE TABLE tocitem CASCADE"))
            
            print("🗑️  删除所有文档...")
            await session.execute(text("TRUNCATE TABLE document CASCADE"))
            
            await session.commit()
            
            print("\n✅ 数据库已彻底清空！")
            print("✨ 现在可以重新入库文档了")
            
        except Exception as e:
            print(f"\n❌ 清空失败：{e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(silent_nuke())
