import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from backend.app.core.config import settings
from backend.app.services.intelligence.galaxy.scout import GalaxyScout
from backend.app.core.models import Galaxy, DocumentGalaxyLink, Document
from sqlalchemy import delete, select

async def cleanup_and_align():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    print("🧹 [Cleanup] 正在清理虚拟测试数据...")
    
    async with async_session() as session:
        # 1. 删除虚拟文档关联
        # 我们通过文件名特征来识别虚拟文档
        mock_docs_stmt = select(Document.id).where(
            (Document.filename.like("quant_%")) | 
            (Document.filename.like("crypto_%")) | 
            (Document.filename.like("noise_%"))
        )
        mock_res = await session.execute(mock_docs_stmt)
        mock_ids = mock_res.scalars().all()
        
        if mock_ids:
            await session.execute(delete(DocumentGalaxyLink).where(DocumentGalaxyLink.document_id.in_(mock_ids)))
            await session.execute(delete(Document).where(Document.id.in_(mock_ids)))
            print(f"   ✅ 已清理 {len(mock_ids)} 个虚拟文档及其关联。")

        # 2. 清空所有星系（因为之前的星系重心被虚拟数据污染了）
        await session.execute(delete(DocumentGalaxyLink))
        await session.execute(delete(Galaxy))
        print("   ✅ 已重置星系主权，准备重建真实索引。")
        
        await session.commit()

        # 3. 真实对齐：将 5 篇真文档投影入库
        print("\n✨ [Alignment] 正在为真实文档建立星系主权...")
        scout = GalaxyScout(session)
        
        real_docs_stmt = select(Document.id, Document.filename).where(Document.status == "completed")
        real_res = await session.execute(real_docs_stmt)
        real_docs = real_res.all()
        
        for doc_id, filename in real_docs:
            print(f"   🚀 投影文档: {filename}...")
            # 调用正式的 V3.1 投影逻辑
            galaxies = await scout.project_document_to_galaxies(doc_id)
            print(f"      ↳ 已归入星系: {galaxies}")

        await session.commit()
        print("\n✅ [Success] 数据清理与真实星系对齐圆满完成。")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(cleanup_and_align())
