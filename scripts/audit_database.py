"""
⚠️ DEPRECATED - Local Database Audit
====================================
This script is deprecated. Local persistence has been phased out in favor of cloud Bitable.
"""
import asyncio
import sys
from pathlib import Path

# 🏛️ 路径锚定
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem, Chunk
from sqlmodel import select

async def main():
    print("🔍 [SpineDoc Audit] 正在扫描知识库...")
    sm = get_async_sessionmaker()
    async with sm() as session:
        # 1. 文档审计
        docs = (await session.execute(select(Document))).scalars().all()
        print(f"\n📂 已入库文档: {len(docs)} 个")
        for d in docs:
            # 统计每个文档的 Chunks 数量
            chunk_count = (await session.execute(
                select(func.count()).select_from(Chunk).where(Chunk.document_id == d.id)
            )).scalar() or 0
            print(f"  - [{str(d.id)[:8]}] {d.filename} (共 {chunk_count} 个分片, 状态: {d.status})")

        # 2. 目录审计
        tocs = (await session.execute(select(TocItem))).scalars().all()
        syn_tocs = [t for t in tocs if t.is_synthetic]
        print(f"\n🧬 逻辑脊梁概况:")
        print(f"  - 总目录项: {len(tocs)}")
        print(f"  - 合成节点: {len(syn_tocs)} (V3.5 涌现成果)")
        
        if syn_tocs:
            print(f"\n✨ 最近合成的章节预览:")
            for t in sorted(syn_tocs, key=lambda x: x.level)[:5]:
                print(f"    [{t.level}] {t.title} (P{t.physical_start}-P{t.physical_end})")

if __name__ == "__main__":
    from sqlalchemy import func
    asyncio.run(main())
