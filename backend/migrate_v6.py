"""
SpineDoc 异步直连迁移脚本 - V6.0 扩展
为 Document 和 TocItem 添加 Offset 及 Embedding 支持
"""
import asyncio
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.config import settings

async def run_migration():
    print("=" * 60)
    print("🚀 正在执行 V6.0 架构字段迁移...")
    print("=" * 60)
    
    db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    
    import asyncpg
    
    try:
        conn = await asyncpg.connect(db_url)
        print(f"🔗 已连接到: {db_url.split('@')[-1]}")
        
        # 1. 为 Document 添加字段
        print("📝 正在加固 Document 表...")
        await conn.execute("ALTER TABLE document ADD COLUMN IF NOT EXISTS is_scanned BOOLEAN DEFAULT FALSE;")
        await conn.execute("ALTER TABLE document ADD COLUMN IF NOT EXISTS page_offset INTEGER DEFAULT 0;")
        
        # 2. 为 TocItem 添加字段
        print("📝 正在加固 TocItem 表...")
        # 增加 Vector 向量支持
        await conn.execute(f"ALTER TABLE tocitem ADD COLUMN IF NOT EXISTS embedding vector({settings.EMBEDDING_DIMENSION});")
        
        await conn.close()
        print("\n🎉 V6.0 数据库结构同步完成。")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_migration())
