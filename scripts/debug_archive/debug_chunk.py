"""
调试 Chunk 原始内容
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.db import get_async_sessionmaker
from sqlmodel import select
from app.core.models import Document, Chunk

async def check():
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        stmt = select(Document).where(Document.filename == '1.pdf')
        doc = (await session.execute(stmt)).scalars().first()
        if doc:
            # 获取前 3 个 chunk
            stmt = select(Chunk).where(Chunk.document_id == doc.id).limit(3)
            chunks = (await session.execute(stmt)).scalars().all()
            for i, c in enumerate(chunks):
                print(f'\n=== Chunk {i+1} ===')
                print(f'P{c.page_number} - {c.breadcrumb}')
                print(f'内容前 300 字符:')
                print(repr(c.content[:300]))

asyncio.run(check())
