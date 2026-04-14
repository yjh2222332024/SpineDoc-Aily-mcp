import asyncio
import sys
import fitz
from pathlib import Path
from sqlalchemy import select, delete
from uuid import uuid4

# 🏛️ 顶级架构锚定
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem
from backend.app.services.parser import hybrid_parser
from backend.app.services.rag.vector_store import PostgresStore

async def force_restore():
    print("🚀 [Force-Restore] 正在通过 HybridParser 强制重建逻辑脊梁...")
    session_maker = get_async_sessionmaker()
    store = PostgresStore()
    
    async with session_maker() as session:
        # 1. 物理锁定文档
        stmt = select(Document).where(Document.filename == '1.pdf').order_by(Document.created_at.desc()).limit(1)
        doc = (await session.execute(stmt)).scalar_one_or_none()
        
        if not doc:
            print("❌ 数据库中未找到 1.pdf 记录。")
            return

        # 2. 物理清空该文档的所有 TOC (确权清空)
        print(f"🧹 清理旧 TOC (Document ID: {str(doc.id)[:8]})...")
        await session.execute(delete(TocItem).where(TocItem.document_id == doc.id))
        await session.commit()

        # 3. 核心参数：复刻 Ingest 时的确权环境
        manual_toc_range = [9, 15]
        manual_offset = 17
        
        print(f"🛰️  启动 VLM 制图师 (Pages: {manual_toc_range})...")
        # 🚀 这里的返回值已经是经过 TOCManager 处理过的 SpineNode 列表
        enriched_toc = await hybrid_parser.extract_toc_async(
            doc.file_path, 
            manual_range=manual_toc_range
        )
        
        print(f"🧬 已获取 {len(enriched_toc)} 个初始节点。执行物理对齐校准...")
        
        # 4. 再次执行 Manager 校准 (确保 Offset 被正确应用)
        # 注意：hybrid_parser 内部可能没用到我们的 manual_offset，这里我们要显式再跑一遍 Manager
        from backend.app.services.toc.manager import toc_manager
        final_toc = toc_manager.process_raw_toc(
            enriched_toc, 
            doc.total_pages, 
            forced_offset=manual_offset,
            toc_physical_range=manual_toc_range
        )

        # 5. 生成 TOC Embedding 并存入
        print(f"📥 正在持久化 {len(final_toc)} 个高质量节点到数据库...")
        titles = [n.title for n in final_toc]
        embeddings = await store.get_embeddings_api(titles)
        
        for i, n in enumerate(final_toc):
            session.add(TocItem(
                id=n.id, title=n.title, page=n.logical_page,
                level=n.level, document_id=doc.id,
                physical_start=n.physical_start, physical_end=n.physical_end,
                embedding=embeddings[i]
            ))
        
        await session.commit()
        print("\n✅ [Success] 脊梁重建完成！1.pdf 已重获逻辑灵魂。")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(force_restore())
