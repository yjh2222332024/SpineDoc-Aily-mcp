"""
🔍 SpineDoc 星系数据库审计脚本 (只读模式)
=========================================
使命：安全检查 Galaxy 表、DocumentGalaxyLink 表的实际状态
纪律：绝对不执行任何 DELETE/UPDATE 操作，只读 SELECT
"""

import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.app.core.config import settings
from backend.app.core.models import Galaxy, DocumentGalaxyLink, Document

async def audit_galaxy_database():
    # 只读引擎
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("=" * 80)
    print("🔍 SpineDoc 星系数据库审计 (只读模式)")
    print("=" * 80)

    async with async_session() as session:
        # --- 1. 文档总览 ---
        print("\n📊 [1] 文档总览")
        print("-" * 40)
        doc_count_stmt = select(func.count(Document.id))
        doc_count = (await session.execute(doc_count_stmt)).scalar()
        print(f"   总文档数：{doc_count}")

        completed_stmt = select(func.count(Document.id)).where(Document.status == "completed")
        completed_count = (await session.execute(completed_stmt)).scalar()
        print(f"   已完成状态：{completed_count}")

        # --- 2. 星系总览 ---
        print("\n🌌 [2] 星系总览")
        print("-" * 40)
        galaxy_count_stmt = select(func.count(Galaxy.id))
        galaxy_count = (await session.execute(galaxy_count_stmt)).scalar()
        print(f"   星系总数：{galaxy_count}")

        if galaxy_count > 0:
            # 列出所有星系及其成员数
            galaxies_stmt = select(Galaxy).order_by(Galaxy.member_count.desc())
            galaxies_result = await session.execute(galaxies_stmt)
            galaxies = galaxies_result.scalars().all()

            print(f"\n   星系详情 (按成员数排序):")
            for i, galaxy in enumerate(galaxies, 1):
                print(f"   {i}. {galaxy.name}")
                print(f"      ├─ 成员数：{galaxy.member_count}")
                print(f"      ├─ 描述：{galaxy.description[:50]}...")
                print(f"      └─ ID: {galaxy.id}")

        # --- 3. 星系连接总览 ---
        print("\n🔗 [3] 星系连接总览 (DocumentGalaxyLink)")
        print("-" * 40)
        link_count_stmt = select(func.count(DocumentGalaxyLink.document_id))
        link_count = (await session.execute(link_count_stmt)).scalar()
        print(f"   连接记录总数：{link_count}")

        if link_count > 0:
            # 统计每个文档关联了多少个星系
            doc_link_count_stmt = select(
                DocumentGalaxyLink.document_id,
                func.count(DocumentGalaxyLink.galaxy_id).label('galaxy_count')
            ).group_by(DocumentGalaxyLink.document_id)
            doc_link_result = (await session.execute(doc_link_count_stmt)).all()

            print(f"\n   文档 - 星系关联分布:")
            association_pattern = {}
            for doc_id, count in doc_link_result:
                association_pattern[count] = association_pattern.get(count, 0) + 1

            for galaxy_count, doc_count in sorted(association_pattern.items()):
                print(f"   关联 {galaxy_count} 个星系的文档：{doc_count} 篇")

        # --- 4. 文档星系映射详情 ---
        print("\n🗺️ [4] 文档星系映射详情")
        print("-" * 40)

        # 获取所有已完成的文档
        docs_stmt = select(Document).where(Document.status == "completed").limit(20)
        docs_result = await session.execute(docs_stmt)
        docs = docs_result.scalars().all()

        for doc in docs:
            # 查询该文档关联的星系
            doc_links_stmt = select(
                DocumentGalaxyLink, Galaxy
            ).join(
                Galaxy, DocumentGalaxyLink.galaxy_id == Galaxy.id
            ).where(
                DocumentGalaxyLink.document_id == doc.id
            )
            doc_links_result = await session.execute(doc_links_stmt)
            links = doc_links_result.all()

            if links:
                galaxy_names = [link[1].name for link in links]
                print(f"   📄 {doc.filename}")
                print(f"      ↳ 关联星系：{', '.join(galaxy_names)}")
            else:
                print(f"   📄 {doc.filename} [⚠️ 未关联任何星系]")

        # --- 5. 孤立文档检测 ---
        print("\n🏝️ [5] 孤立文档检测")
        print("-" * 40)

        # 查找没有关联任何星系的文档
        isolated_docs_stmt = select(Document).where(
            Document.status == "completed",
            ~Document.galaxy_links.any()
        ).limit(10)
        isolated_result = await session.execute(isolated_docs_stmt)
        isolated_docs = isolated_result.scalars().all()

        if isolated_docs:
            print(f"   发现 {len(isolated_docs)} 篇孤立文档 (未关联任何星系):")
            for doc in isolated_docs:
                print(f"      - {doc.filename}")
        else:
            print("   ✅ 所有已完成文档都已关联星系")

        # --- 6. 星系成员详情 ---
        print("\n🌟 [6] 星系成员详情")
        print("-" * 40)

        if galaxies:
            for galaxy in galaxies[:5]:  # 只显示前 5 个星系
                members_stmt = select(
                    DocumentGalaxyLink, Document
                ).join(
                    Document, DocumentGalaxyLink.document_id == Document.id
                ).where(
                    DocumentGalaxyLink.galaxy_id == galaxy.id
                )
                members_result = await session.execute(members_stmt)
                members = members_result.all()

                print(f"   🌌 {galaxy.name} ({galaxy.member_count} 成员):")
                for link, doc in members[:10]:  # 每星系最多显示 10 个成员
                    print(f"      - {doc.filename} (relevance: {link.relevance_score:.2f})")
                if len(members) > 10:
                    print(f"      ... 还有 {len(members) - 10} 个成员")

    print("\n" + "=" * 80)
    print("✅ 审计完成 (只读模式，未执行任何修改操作)")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(audit_galaxy_database())
