import asyncio
from sqlalchemy import text
from app.core.db import get_async_engine

async def probe_full_schema():
    engine = get_async_engine()
    async with engine.connect() as conn:
        tables = ['document', 'tocitem', 'chunk']
        print("\n🏛️  PostgreSQL Full Ground Truth Audit")
        
        for table in tables:
            result = await conn.execute(text(
                f"SELECT column_name, is_nullable, column_default, data_type "
                f"FROM information_schema.columns "
                f"WHERE table_name = '{table}' "
                f"ORDER BY column_name"
            ))
            
            print(f"\n[Table: {table.upper()}]")
            print("-" * 70)
            for row in result:
                print(f"Column: {row[0]:<20} | Nullable: {row[1]:<5} | Type: {row[3]:<15} | Default: {row[2]}")
            print("-" * 70)

if __name__ == "__main__":
    asyncio.run(probe_full_schema())
