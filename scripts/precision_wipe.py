import asyncio
from sqlalchemy import text
from app.core.db import get_async_engine

async def precision_wipe():
    engine = get_async_engine()
    filenames = ['2502.01113v3.pdf', '2502.12342v1.pdf', 'paper_1.pdf']
    
    # 1. 首先获取 ID (独立连接)
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT id FROM document WHERE filename = ANY(:names)"),
            {"names": filenames}
        )
        doc_ids = [row[0] for row in result]
    
    if not doc_ids:
        print("⚠️ [Wipe] 未发现匹配记录，可能已被清理。")
        return

    print(f"📡 [Wipe] 锁定文档 ID: {[str(i)[:8] for i in doc_ids]}")

    # 2. 逐个表进行原子化物理抹除
    # 我们只针对探测脚本确认存在的表
    tables = ['chunk', 'tocitem', 'processingmetric', 'document']
    
    for table in tables:
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text(f"DELETE FROM {table} WHERE {'document_id' if table != 'document' else 'id'} = ANY(:ids)"),
                    {"ids": doc_ids}
                )
                print(f"✅ [Wipe] 表 {table.upper()} 已清理。")
        except Exception as e:
            print(f"❌ [Wipe] 表 {table.upper()} 清理失败 (可能不存在): {e}")

    print(f"✨ [Wipe] 全量物理抹除完成。")

if __name__ == "__main__":
    asyncio.run(precision_wipe())
