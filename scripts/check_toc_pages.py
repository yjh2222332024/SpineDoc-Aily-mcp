"""查看 SM4 相关 TOC 的页码设置"""
import asyncio
from sqlmodel import select
from app.core.db import get_async_sessionmaker
from app.core.models import TocItem

async def test():
    async with get_async_sessionmaker()() as s:
        # 查看 SM4 相关的 TOC
        toc = (await s.execute(
            select(TocItem)
            .where(TocItem.title.like('%SM4%'))
            .order_by(TocItem.page)
        )).scalars().all()
        
        print("SM4 相关的 TOC 项:")
        for t in toc:
            print(f'  {t.title}: page={t.page}, physical_start={t.physical_start}, physical_end={t.physical_end}')
        
        # 查看前 20 个 TOC 项的顺序
        all_toc = (await s.execute(
            select(TocItem)
            .order_by(TocItem.page)
            .limit(20)
        )).scalars().all()
        
        print("\n前 20 个 TOC 项的顺序:")
        for t in all_toc:
            print(f'  P{t.page}: {t.title} (physical: {t.physical_start}-{t.physical_end})')

asyncio.run(test())
