"""检查数据库中 Chunk 的页码分布"""
import asyncio
from sqlmodel import select
from app.core.db import get_async_sessionmaker
from app.core.models import Chunk, TocItem

async def check():
    async with get_async_sessionmaker()() as s:
        # 检查 Chunk 页码分布
        chunks = (await s.execute(select(Chunk).order_by(Chunk.page_number).limit(50))).scalars().all()
        
        print("Chunk 页码分布:")
        page_counts = {}
        for c in chunks:
            page = c.page_number
            page_counts[page] = page_counts.get(page, 0) + 1
        
        # 按页码排序显示
        for page in sorted(page_counts.keys())[:20]:
            print(f"  P{page}: {page_counts[page]} 个 Chunk")
        
        print(f"\n总 Chunk 数：{len(chunks)}")
        print(f"涉及的页码范围：P{min(page_counts.keys())} - P{max(page_counts.keys())}")
        
        # 检查 TOC 项
        print("\nTOC 项分布:")
        tocs = (await s.execute(select(TocItem).order_by(TocItem.physical_start).limit(20))).scalars().all()
        for t in tocs:
            print(f"  {t.title}: physical_start={t.physical_start}, physical_end={t.physical_end}")

asyncio.run(check())
