"""
SpineDoc V6.5 终极护城河迁移脚本
添加关键词反哺、物理疆域映射等核心字段。
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
    print("🚀 正在执行 V6.5 终极护城河字段迁移...")
    print("=" * 60)
    
    db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    
    import asyncpg
    
    try:
        conn = await asyncpg.connect(db_url)
        print(f"🔗 数据库已连接")
        
        # 1. 为 TocItem 增加语义增强字段
        print("📝 正在加固 TocItem 语义中枢...")
        await conn.execute("ALTER TABLE tocitem ADD COLUMN IF NOT EXISTS keywords JSONB;")
        await conn.execute(f"ALTER TABLE tocitem ADD COLUMN IF NOT EXISTS keyword_embedding vector({settings.EMBEDDING_DIMENSION});")
        
        # 2. 为 TocItem 增加物理疆域字段
        print("📝 正在标定 TocItem 物理疆域字段...")
        await conn.execute("ALTER TABLE tocitem ADD COLUMN IF NOT EXISTS physical_start INTEGER DEFAULT 0;")
        await conn.execute("ALTER TABLE tocitem ADD COLUMN IF NOT EXISTS physical_end INTEGER DEFAULT 0;")
        await conn.execute("ALTER TABLE tocitem ADD COLUMN IF NOT EXISTS offset_verified BOOLEAN DEFAULT FALSE;")
        
        await conn.close()
        print("\n🎉 V6.5 物理架构升级完成。SpineDoc 已具备『炼丹』基础。")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")

if __name__ == "__main__":
    asyncio.run(run_migration())
