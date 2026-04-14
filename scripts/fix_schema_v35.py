import asyncio
import sys
from pathlib import Path

# 🏛️ 路径锚定：顶级架构师的绝对基准
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.app.core.db import get_async_sessionmaker
from sqlalchemy import text

async def main():
    print("🛠️ 正在修复数据库 Schema...")
    sm = get_async_sessionmaker()
    async with sm() as session:
        try:
            # 强行注入 is_synthetic 字段
            await session.execute(text("ALTER TABLE tocitem ADD COLUMN IF NOT EXISTS is_synthetic BOOLEAN DEFAULT FALSE"))
            await session.commit()
            print("✅ 修复成功：is_synthetic 字段已就绪。")
        except Exception as e:
            print(f"❌ 修复失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())
