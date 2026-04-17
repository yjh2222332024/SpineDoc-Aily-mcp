import asyncio
import sys
import os

# 🚀 确保可以找到 backend 包
sys.path.append(os.getcwd())

from backend.app.core.db import init_db
import backend.app.core.models # 🚀 显式加载模型，确保 metadata 完整注册

async def main():
    print("🏛️ [Schema] 正在执行星系物理同步 (仅增量创建缺失表)...")
    try:
        # init_db 内部调用的是 create_all，它是非破坏性的。
        await init_db()
        print("✅ [Schema] 物理同步完成。现有数据不受影响。")
    except Exception as e:
        print(f"❌ [Schema] 同步失败: {e}")

if __name__ == "__main__":
    asyncio.run(main())
