"""
⚖️ Galaxy Sovereignty Realigner - 星系主权重组员
===============================================
职责：基于 V3.0 工业级治理逻辑，彻底重组现有数据库中的星系聚类。
纪律：物理重置关联，执行语义引力合并。
"""

import asyncio
import sys
import numpy as np
from pathlib import Path
from sqlalchemy import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession

# 🏛️ 路径锚定
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, Galaxy, DocumentGalaxyLink
from backend.app.services.intelligence.clustering.scout import GalaxyScout

async def realign_all_galaxies():
    print("\n" + "🏛️  " * 20)
    print("🚀 [Realigner] 启动全量星系主权重组...")
    print("🏛️  " * 20)

    session_maker = get_async_sessionmaker()
    
    async with session_maker() as session:
        # 1. 备份并清理旧关联
        print("\n🧹 [Step 1] 正在物理清理旧世界关联 (DocumentGalaxyLink)...")
        await session.execute(delete(DocumentGalaxyLink))
        
        # 将现有星系的 member_count 重置为 0，以便重新计算重心
        print("🔄 [Step 1] 重置星系人口计数...")
        from sqlalchemy import update
        await session.execute(update(Galaxy).values(member_count=0))
        
        # 2. 获取所有已完成的文档
        stmt = select(Document).where(Document.status == "completed")
        result = await session.execute(stmt)
        docs = result.scalars().all()
        print(f"📡 发现 {len(docs)} 篇待重组文档。")

        # 3. 初始化新一代侦察员 (它已经装载了 AdvancedAnchorAuditor)
        scout = GalaxyScout(session)

        # 4. 逐一执行工业级投影
        print("\n🧬 [Step 2] 正在执行语义引力重组与锚点审计...")
        for i, doc in enumerate(docs, 1):
            print(f"   [{i}/{len(docs)}] 正在处理: {doc.filename[:30]}...")
            # 🚀 这里会触发我们写的相似度归并与审计逻辑
            projected = await scout.project_document_to_galaxies(doc.id)
            print(f"     ↳ 映射至: {projected}")

        # 5. 清理僵尸星系 (没有成员的星系)
        print("\n🗑️ [Step 3] 正在物理切除僵尸星系 (member_count == 0)...")
        zombie_stmt = delete(Galaxy).where(Galaxy.member_count == 0)
        await session.execute(zombie_stmt)

        await session.commit()
        print("\n" + "✅ " * 20)
        print("🏆 [Success] 数据库语义星系重组完成！新秩序已确立。")
        print("✅ " * 20)

        # 6. 最后一步：触发 Thesaurus Map 更新
        print("\n🗺️ [Step 4] 正在根据新秩序刷新 Thesaurus Map...")
        from scripts.generate_thesaurus_map import generate_thesaurus_map
        await generate_thesaurus_map()

if __name__ == "__main__":
    asyncio.run(realign_all_galaxies())
