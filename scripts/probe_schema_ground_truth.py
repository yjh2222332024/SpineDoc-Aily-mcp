import asyncio
from sqlalchemy import text
from app.core.db import get_async_engine

async def probe_schema():
    engine = get_async_engine()
    async with engine.connect() as conn:
        # 获取 document 表的所有列
        result = await conn.execute(text(
            "SELECT column_name, is_nullable, column_default, data_type "
            "FROM information_schema.columns "
            "WHERE table_name = 'document' "
            "ORDER BY column_name"
        ))
        
        print("\n🏛️  PostgreSQL Ground Truth: Table 'document'")
        print("-" * 60)
        for row in result:
            print(f"Column: {row[0]:<20} | Nullable: {row[1]:<5} | Type: {row[3]:<15} | Default: {row[2]}")
        print("-" * 60)

if __name__ == "__main__":
    asyncio.run(probe_schema())
