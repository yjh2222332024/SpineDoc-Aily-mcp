"""
SpineDoc 物理数据库巡检工具
职责：直接透视 Postgres 核心表，检查数据对齐与内容完整性。
"""
import asyncio
import os
import sys
from pathlib import Path
from sqlmodel import select, func

# 添加项目路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import get_async_sessionmaker
from app.core.models import Document, TocItem, Chunk

async def inspect():
    print("\n" + "=".center(60, "="))
    print("🛰️ SpineDoc 数据库物理透视".center(60))
    print("=".center(60, "="))
    
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        # 1. 检查 Document
        docs = (await session.execute(select(Document))).scalars().all()
        if not docs:
            print("❌ 数据库中无任何文档记录。")
            return

        for doc in docs:
            print(f"\n📄 文档: {doc.filename}")
            print(f"   ┣ ID: {doc.id}")
            print(f"   ┣ 状态: {doc.status}")
            print(f"   ┣ 物理页总数: {doc.total_pages}")
            print(f"   ┗ 标定 Offset: {doc.page_offset}")

            # 2. 检查 TocItem (脊梁)
            toc_count = (await session.execute(select(func.count(TocItem.id)).where(TocItem.document_id == doc.id))).scalar()
            print(f"   🌳 目录层级: {toc_count} 条记录")
            
            # 抽样检查脊梁是否扭曲
            sample_toc = (await session.execute(select(TocItem).where(TocItem.document_id == doc.id).order_by(TocItem.page).limit(5))).scalars().all()
            print(f"   ┣ 脊梁抽样 (前5条):")
            for t in sample_toc:
                print(f"   ┃   - {t.title[:20]:<20} -> Phys Page: {t.page}")

            # 3. 检查 Chunk (矿石)
            chunk_count = (await session.execute(select(func.count(Chunk.id)).where(Chunk.document_id == doc.id))).scalar()
            print(f"   📦 正文分块: {chunk_count} 片")
            
            if chunk_count > 0:
                # 检查页码 0 异常
                zero_p_count = (await session.execute(select(func.count(Chunk.id)).where(Chunk.document_id == doc.id, Chunk.page_number == 0))).scalar()
                print(f"   ┣ 页码异常 (Page=0): {zero_p_count} 片 {'🚨' if zero_p_count > 0 else '✅'}")
                
                # 抽样检查内容
                sample_chunks = (await session.execute(select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.page_number).limit(3))).scalars().all()
                print(f"   ┗ 内容抽样 (前3片):")
                for c in sample_chunks:
                    snippet = c.content.replace('\n', ' ')[:80]
                    print(f"       [P{c.page_number}] {snippet}...")
            else:
                print(f"   ┗ 🚨 警告：无正文内容落库！")

if __name__ == "__main__":
    try:
        asyncio.run(inspect())
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
