"""
SpineDoc 性能基准测试与召回率审计 (V1.0)
职责：
1. 暴力扫描数据库，建立 Ground Truth。
2. 模拟检索，计算召回率。
3. 审计 TOC 与正文的对齐准确度。
"""
import asyncio
import os
import sys
from pathlib import Path
from sqlmodel import select, func

# 添加项目路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.core.db import get_async_sessionmaker
from app.core.models import Chunk, TocItem, Document
from spine_cli.core.engine import SpineEngine

async def run_benchmark():
    print("\n" + "="*60)
    print("📈 SpineDoc 质量与召回率基准测试")
    print("="*60)

    filename = "1.pdf"
    engine = SpineEngine()
    session_maker = get_async_sessionmaker()
    
    async with session_maker() as session:
        # 1. 寻找文档
        doc = (await session.execute(select(Document).where(Document.filename == filename))).scalars().first()
        if not doc:
            print("❌ 错误：数据库中无此文档。")
            return
        doc_id = str(doc.id)

        # 2. 建立 Ground Truth (暴力搜索所有包含 '抗量子' 的物理页)
        print(f"🔍 正在建立 Ground Truth (暴力扫描数据库)...")
        gt_stmt = select(Chunk.page_number).where(
            Chunk.document_id == doc.id,
            Chunk.content.contains("抗量子")
        )
        gt_pages = set((await session.execute(gt_stmt)).scalars().all())
        print(f"📍 '抗量子' 实际出现的物理页: {sorted(list(gt_pages))}")

        # 3. 运行 RAG 检索测试
        query = "查找文档中关于‘抗量子计算密码’的描述"
        print(f"🔥 模拟检索 Query: '{query}'")
        results = await engine.hybrid_ask(query, doc_id, limit=10)
        
        retrieved_pages = set()
        for res in results:
            # 提取 Snippet 中的 PAGE 标记
            import re
            p_match = re.search(r'\[PAGE: (\d+)\]', res.get('content', ''))
            if p_match:
                retrieved_pages.add(int(p_match.group(1)))

        print(f"📡 RAG 召回的物理页: {sorted(list(retrieved_pages))}")

        # 4. 计算指标
        hits = gt_pages.intersection(retrieved_pages)
        recall = len(hits) / len(gt_pages) if gt_pages else 0
        
        print("\n" + "-"*30)
        print(f"✅ 命中页数: {len(hits)}")
        print(f"📊 召回率 (Recall): {recall:.2%}")
        print(f"🎯 检索精度 (Precision): {len(hits)/len(retrieved_pages):.2%}" if retrieved_pages else "N/A")
        print("-"*30)

        # 5. 审计 TOC 树健康度
        print(f"\n🌳 TOC 脊梁审计 (前 15 条):")
        tocs = (await session.execute(select(TocItem).where(TocItem.document_id == doc.id).order_by(TocItem.page).limit(15))).scalars().all()
        for t in tocs:
            print(f"   [{t.level}] {t.title[:30]:<30} -> Phys Page: {t.page}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
