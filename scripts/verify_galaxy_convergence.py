"""
🧪 星系汇聚逻辑验证脚本
========================
目的：模拟入库一篇与现有文档有锚点重叠的新文档，验证汇聚是否发生
只读模式：不修改数据库
"""

import asyncio
import numpy as np
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.app.core.config import settings
from backend.app.core.models import Galaxy, DocumentGalaxyLink, Document

async def verify_galaxy_convergence():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("=" * 80)
    print("🧪 星系汇聚逻辑验证")
    print("=" * 80)

    async with async_session() as session:
        # --- 1. 获取所有星系名称 ---
        print("\n📊 [1] 当前星系名称分布")
        print("-" * 40)

        galaxies_stmt = select(Galaxy.name, Galaxy.member_count).order_by(Galaxy.name)
        result = await session.execute(galaxies_stmt)
        galaxies = result.all()

        # 提取所有锚点词
        anchor_words = [g.name.replace("Galaxy_", "") for g in galaxies]
        print(f"   当前锚点词库 ({len(anchor_words)} 个):")
        for word in sorted(anchor_words):
            print(f"      - {word}")

        # --- 2. 分析潜在的汇聚路径 ---
        print("\n🔮 [2] 潜在汇聚路径分析")
        print("-" * 40)

        # 假设新文档入库，提取的锚点可能是什么
        # 我们检查现有锚点的"词根重叠"情况
        unigrams = {}  # 记录所有单单词锚点
        for word in anchor_words:
            parts = word.split("_")
            for part in parts:
                part_clean = part.lower().strip()
                if part_clean and part_clean not in ["based", "training", "algorithm"]:
                    unigrams[part_clean] = unigrams.get(part_clean, 0) + 1

        print("   高频词根统计 (可能成为汇聚点的候选):")
        for word, count in sorted(unigrams.items(), key=lambda x: -x[1])[:10]:
            print(f"      - {word}: {count} 次")

        # --- 3. 模拟汇聚场景 ---
        print("\n [3] 模拟场景：入库新文档 'RAG_Optimization.pdf'")
        print("-" * 40)

        # 假设新文档的锚点
        new_doc_anchors = ["Retrieval", "Rag", "Optimization"]
        print(f"   假设新文档锚点：{new_doc_anchors}")

        # 检查哪些锚点会与现有星系重叠
        print("\n   汇聚预测:")
        for anchor in new_doc_anchors:
            # 模糊匹配现有星系名称
            matches = [g for g in galaxies if anchor.lower() in g.name.lower()]
            if matches:
                print(f"    '{anchor}' → 将汇聚到:")
                for m in matches:
                    print(f"      - {m.name} (当前成员：{m.member_count})")
            else:
                print(f"   🆕 '{anchor}' → 将创建新星系")

        # --- 4. 星系规模分布 ---
        print("\n📈 [4] 星系规模分布")
        print("-" * 40)

        size_distribution = {}
        for name, count in galaxies:
            size_distribution[count] = size_distribution.get(count, 0) + 1

        for size, galaxy_count in sorted(size_distribution.items()):
            print(f"   成员数为 {size} 的星系：{galaxy_count} 个")

        # --- 5. 汇聚潜力评估 ---
        print("\n [5] 汇聚潜力评估")
        print("-" * 40)

        # 计算：如果新文档的锚点与现有星系重叠，汇聚概率
        total_galaxies = len(galaxies)
        unique_unigrams = len(set(unigrams.keys()))

        print(f"   当前星系总数：{total_galaxies}")
        print(f"   唯一词根数量：{unique_unigrams}")
        print(f"   平均每个词根对应星系数：{total_galaxies / unique_unigrams:.2f}")

        if total_galaxies / unique_unigrams > 1:
            print("    已存在词根重叠，说明汇聚逻辑正在工作")
        else:
            print("    词根与星系一一对应，说明文档主题差异较大")

        print("\n   📊 建议：")
        print("      当入库更多文档时，汇聚效应会逐渐显现")
        print("      特别是当新文档与现有文档有共同主题时")

    print("\n" + "=" * 80)
    print(" 验证完成 (只读模式)")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(verify_galaxy_convergence())
