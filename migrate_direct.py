"""
SpineDoc 异步直连迁移脚本
直接使用 asyncpg 执行 SQL，绕过 SQLAlchemy 驱动限制
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
    print("🚀 正在通过 asyncpg 执行直接迁移...")
    print("=" * 60)
    
    # 获取数据库连接参数
    # 异步驱动 URL 格式: postgresql+asyncpg://user:pass@host:port/db
    # asyncpg.connect 需要: postgresql://user:pass@host:port/db
    db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    
    import asyncpg
    
    try:
        conn = await asyncpg.connect(db_url)
        print(f"🔗 已连接到: {db_url.split('@')[-1]}")
        
        # 1. 检查列是否存在
        check_sql = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='chunk' AND column_name='metadata_json';
        """
        exists = await conn.fetchval(check_sql)
        
        if exists:
            print("✅ 字段 'metadata_json' 已存在，无需修改。")
        else:
            print("📝 正在添加 'metadata_json' 字段...")
            await conn.execute("ALTER TABLE chunk ADD COLUMN metadata_json JSONB DEFAULT '{}'::jsonb;")
            print("✅ 字段添加成功！")
            
        await conn.close()
        print("\n🎉 数据库结构已同步至 V5.0 版本。")
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_migration())
