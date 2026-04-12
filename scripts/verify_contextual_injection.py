"""
验证 V29.0 上下文摘要注入是否成功
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.db import get_async_sessionmaker
from sqlmodel import select
from app.core.models import TocItem, Document

async def verify_contextual_injection():
    session_maker = get_async_sessionmaker()
    
    async with session_maker() as session:
        # 查找文档
        stmt = select(Document).where(Document.filename == "1.pdf")
        docs = (await session.execute(stmt)).scalars().all()
        
        if not docs:
            print("❌ 数据库中没有 1.pdf 的记录")
            return
        
        doc = docs[0]
        print(f"📄 文档：{doc.filename}")
        print(f"   总页数：{doc.total_pages}")
        print(f"   is_scanned: {doc.is_scanned}")
        
        # 查找 TOC 项（带摘要）
        stmt = select(TocItem).where(TocItem.document_id == doc.id)
        toc_items = (await session.execute(stmt)).scalars().all()
        
        print(f"\n📋 TOC 项数量：{len(toc_items)}")
        
        # 统计有摘要的 TOC 项
        with_summary = [t for t in toc_items if t.summary]
        with_keywords = [t for t in toc_items if t.keywords]
        with_embedding = [t for t in toc_items if t.embedding]
        
        print(f"\n📊 上下文注入统计:")
        print(f"   有摘要的 TOC 项：{len(with_summary)}/{len(toc_items)} ({len(with_summary)/len(toc_items)*100:.1f}%)")
        print(f"   有关键词的 TOC 项：{len(with_keywords)}/{len(toc_items)} ({len(with_keywords)/len(toc_items)*100:.1f}%)")
        print(f"   有向量的 TOC 项：{len(with_embedding)}/{len(toc_items)} ({len(with_embedding)/len(toc_items)*100:.1f}%)")
        
        # 抽样显示
        print(f"\n📝 摘要抽样检查 (前 5 个):")
        for i, item in enumerate(toc_items[:5]):
            print(f"\n[{i+1}] {item.title}")
            print(f"    页码：{item.page} (逻辑) / {item.physical_start} (物理)")
            print(f"    摘要：{item.summary[:100] if item.summary else '❌ 无摘要'}...")
            print(f"    关键词：{item.keywords[:5] if item.keywords else '❌ 无关键词'}...")
        
        # 评估注入质量
        if len(with_summary) / len(toc_items) >= 0.8:
            print(f"\n✅ 上下文摘要注入成功！({len(with_summary)/len(toc_items)*100:.1f}%)")
        elif len(with_summary) / len(toc_items) >= 0.5:
            print(f"\n⚠️ 上下文摘要注入部分成功 ({len(with_summary)/len(toc_items)*100:.1f}%)")
        else:
            print(f"\n❌ 上下文摘要注入失败 ({len(with_summary)/len(toc_items)*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(verify_contextual_injection())
