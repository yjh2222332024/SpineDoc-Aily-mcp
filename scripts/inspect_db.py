""" 数据库探查脚本 - 查看 TOC 树和切片概况"""
import sys
sys.path.insert(0, '.')

import asyncio
from sqlmodel import select
from backend.app.core.models import Document, TocItem, Chunk

async def inspect_db():
    from backend.app.services.rag.vector_store import PostgresStore
    store = PostgresStore()
    async with store._session_maker() as session:
        # 1. 列出所有文档
        print("="*60)
        print(" 文档列表")
        print("="*60)
        stmt = select(Document).order_by(Document.created_at.desc())
        docs = (await session.execute(stmt)).scalars().all()

        for doc in docs:
            print(f"\n {doc.filename}")
            print(f"   ID: {doc.id}")
            print(f"   总页数：{doc.total_pages}")
            print(f"   状态：{doc.status}")
            print(f"   是否扫描件：{doc.is_scanned}")
            print(f"   Page Offset: {doc.page_offset}")
            print(f"   创建时间：{doc.created_at}")

        # 2. 每个文档的 TOC 树
        print("\n" + "="*60)
        print("🌳 TOC 逻辑脊梁")
        print("="*60)

        for doc in docs:
            stmt_toc = select(TocItem).where(TocItem.document_id == doc.id).order_by(TocItem.page)
            toc_items = (await session.execute(stmt_toc)).scalars().all()

            print(f"\n📖 {doc.filename} - {len(toc_items)} 个目录项")

            # 构建树形结构
            nodes = {0: "ROOT"}
            for item in toc_items:
                indent = "  " * (item.level - 1)
                marker = "└─" if item.level > 1 else "•"
                print(f"   {indent}{marker} P{item.page} [{item.level}] {item.title}")

        # 3. 切片概况
        print("\n" + "="*60)
        print("🔪 切片概况 (每个文档前 10 个)")
        print("="*60)

        for doc in docs:
            stmt_chunks = select(Chunk).where(Chunk.document_id == doc.id).limit(10)
            chunks = (await session.execute(stmt_chunks)).scalars().all()

            stmt_count = select(Chunk.id).where(Chunk.document_id == doc.id)
            total = (await session.execute(stmt_count)).scalars().all()

            print(f"\n📖 {doc.filename} - 共 {len(total)} 个切片 (显示前 10)")

            for i, chunk in enumerate(chunks):
                content_preview = chunk.content[:60].replace('\n', ' ')
                print(f"   [{i+1}] P{chunk.page_number} | L{chunk.level}")
                print(f"       {content_preview}...")
                if chunk.logic_tags:
                    print(f"       标签：{chunk.logic_tags[:5]}")

asyncio.run(inspect_db())
