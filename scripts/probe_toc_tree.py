import asyncio
from sqlalchemy import text
from app.core.db import get_async_engine

async def probe_toc_tree():
    engine = get_async_engine()
    async with engine.connect() as conn:
        print("\n🏛️  PostgreSQL TOC Hierarchy Audit")
        
        # 获取最近入库的文档
        doc_result = await conn.execute(text("SELECT id, filename FROM document ORDER BY created_at DESC LIMIT 3"))
        docs = doc_result.all()
        
        for doc_id, filename in docs:
            print(f"\n[Document: {filename} ({str(doc_id)[:8]})]")
            print("-" * 80)
            
            # 探测 TOC 项及其层级、页码
            toc_result = await conn.execute(
                text("SELECT title, page, level, physical_start, physical_end FROM tocitem WHERE document_id = :id ORDER BY page, level"),
                {"id": doc_id}
            )
            
            for row in toc_result:
                print(f"L{row[2]} | P{row[1]:<3} | Phys: {row[3]:>2}-{row[4]:<2} | Title: {row[0]}")
            print("-" * 80)

if __name__ == "__main__":
    asyncio.run(probe_toc_tree())
