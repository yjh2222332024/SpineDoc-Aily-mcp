"""
SpineDoc 原子测试：逻辑涌现全链路验证 (V3.5)
===========================================
测试目标：验证无 Outline 文档是否能自动生成合成脊梁并归一化入库。
"""
import asyncio
import os
import sys
from pathlib import Path

# 🏛️ 路径锚定
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from spine_cli.core.engine import SpineEngine
from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import TocItem, Chunk, Document
from sqlmodel import select

async def run_atomic_test():
    engine = SpineEngine()
    test_pdf = "ceshi_ocr/2401.08406v3.pdf"
    
    print(f"\n🚀 [Step 1] 启动逻辑收割：{test_pdf}")
    # 🚀 [V3.5] 强制开启逻辑涌现模式，测试合成脊梁算法
    result = await engine.ingest_document(test_pdf, force=True, force_emergent=True)
    
    doc_id = result["id"]
    print(f"✅ 文档入库成功，ID: {doc_id}")

    print("\n🔍 [Step 2] 执行法医级数据审计...")
    async_session = get_async_sessionmaker()
    async with async_session() as session:
        # 1. 审计 TocItems (合成脊梁)
        stmt_toc = select(TocItem).where(TocItem.document_id == doc_id, TocItem.is_synthetic == True)
        toc_items = (await session.execute(stmt_toc)).scalars().all()
        
        print(f"📊 发现合成脊梁节点: {len(toc_items)} 个")
        for it in sorted(toc_items, key=lambda x: (x.level, x.physical_start)):
            print(f"  [{it.level}] {it.title} (P{it.physical_start}-P{it.physical_end})")

        # 2. 审计 Chunks (语义反哺)
        stmt_chunk = select(Chunk).where(Chunk.document_id == doc_id).limit(10)
        chunks = (await session.execute(stmt_chunk)).scalars().all()
        
        print(f"\n🧩 抽取 10 个原子分片进行路径审计:")
        for c in chunks:
            print(f"  [P{c.page_number}] Breadcrumb: {c.breadcrumb}")
            print(f"  [Tags] {', '.join(c.logic_tags[:5]) if c.logic_tags else '[Empty]'}")
            print("-" * 30)

        # 3. 核心断言
        assert len(toc_items) > 0, "❌ 错误：未能生成合成脊梁！"
        assert all(c.breadcrumb != "[Full Document]" for c in chunks), "❌ 错误：语义反哺失败，breadcrumb 仍为默认值！"
        assert any(it.level == -3 for it in toc_items), "❌ 错误：未能生成 Level -3 主权章节！"

    print("\n🏆 [SUCCESS] SpineDoc 3.5 逻辑涌现架构通过原子测试！")

if __name__ == "__main__":
    asyncio.run(run_atomic_test())
