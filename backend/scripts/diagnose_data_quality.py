"""
SpineDoc 数据质量深度诊断工具
用途：检查特定文档的入库完整度、OCR 质量以及物理-逻辑对齐状态。
"""
import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID

# 添加项目路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.db import get_async_sessionmaker
from app.core.models import Document, TocItem, Chunk
from sqlmodel import select, func

async def diagnose(filename: str):
    print("=" * 60)
    print(f"🔍 正在诊断文档: {filename}")
    print("=" * 60)
    
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        # 1. 查找文档
        doc_stmt = select(Document).where(Document.filename == filename)
        doc = (await session.execute(doc_stmt)).scalars().first()
        
        if not doc:
            print(f"❌ 错误：数据库中找不到文件 '{filename}'")
            return

        print(f"🆔 文档 ID: {doc.id}")
        print(f"📊 状态: {doc.status}")
        print(f"📄 总物理页数: {doc.total_pages}")
        print(f"⚖️ 标定 Offset: {doc.page_offset}")
        
        # 2. 检查 TOC 完整度
        toc_count_stmt = select(func.count(TocItem.id)).where(TocItem.document_id == doc.id)
        toc_count = (await session.execute(toc_count_stmt)).scalar() or 0
        print(f"🌳 目录条目 (TocItems): {toc_count}")

        # 3. 检查正文分块 (Chunks)
        chunk_stmt = select(Chunk).where(Chunk.document_id == doc.id).limit(5)
        chunks = (await session.execute(chunk_stmt)).scalars().all()
        
        chunk_count_stmt = select(func.count(Chunk.id)).where(Chunk.document_id == doc.id)
        chunk_count = (await session.execute(chunk_count_stmt)).scalar() or 0
        print(f"📦 已入库分块 (Chunks): {chunk_count}")
        
        if chunk_count > 0:
            print("\n📝 抽样检查前 3 个分块内容:")
            for i, c in enumerate(chunks[:3]):
                snippet = c.content.replace('\n', ' ')[:100]
                print(f"   [{i+1}] Page {c.page_number} | Breadcrumb: {c.breadcrumb}")
                print(f"       Text: {snippet}...")
        else:
            print("\n🚨 警告：数据库中没有正文分块！检索肯定会失败。")

        # 4. 判定健康度
        if doc.status == "COMPLETED" and chunk_count < (doc.total_pages * 0.1):
            print("\n❌ 诊断结论：数据极度缺失 (残次品)！")
            print("👉 原因：可能是之前的 OCR 进程中途崩溃或 429 导致未能保存分块。")
        elif doc.status == "COMPLETED":
            print("\n✅ 诊断结论：文档结构健康，可以进行检索测试。")
        else:
            print("\n⏳ 诊断结论：文档处理未完成或失败。")

if __name__ == "__main__":
    asyncio.run(diagnose("1.pdf"))
