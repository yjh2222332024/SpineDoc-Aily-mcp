"""查找包含 SM4 的 Chunk"""
import asyncio
from sqlmodel import select
from app.core.db import get_async_sessionmaker
from app.core.models import Chunk

async def test():
    async with get_async_sessionmaker()() as s:
        # 查找包含 SM4 的 Chunk
        chunks = (await s.execute(
            select(Chunk).where(Chunk.content.like('%SM4%')).limit(10)
        )).scalars().all()
        
        print(f'找到 {len(chunks)} 个包含 SM4 的 Chunk:')
        for c in chunks:
            print(f'  P{c.page_number}: {c.breadcrumb}')
        
        # 查找 SM4 相关的 TOC
        from app.core.models import TocItem
        toc_items = (await s.execute(
            select(TocItem).where(TocItem.title.like('%SM4%'))
        )).scalars().all()
        
        print(f'\n找到 {len(toc_items)} 个包含 SM4 的目录项:')
        for t in toc_items:
            print(f'  P{t.physical_start}-{t.physical_end}: {t.title}')

asyncio.run(test())
