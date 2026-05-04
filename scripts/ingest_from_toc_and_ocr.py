import asyncio
import sys
import json
import time
import fitz
from pathlib import Path
from rich.console import Console
from sqlalchemy import select, delete
from uuid import UUID

# 🏛️ 顶级架构锚定
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem, Chunk, ProcessingStatus
from backend.app.services.ocr.body_alchemist import BodyAlchemist
from backend.app.services.ingestion.splitter import structural_splitter
from backend.app.services.ingestion.logic_refiner import LogicRefiner
from backend.app.services.toc.base import SpineNode

console = Console()

async def ingest_fast_track():
    console.print("[bold cyan]🚀 [Fast-Track] 启动脊梁驱动型全量入库流水线 (V52.0)...[/bold cyan]")
    
    session_maker = get_async_sessionmaker()
    alchemist = BodyAlchemist()
    refiner = LogicRefiner(threshold=0.25)
    
    async with session_maker() as session:
        # 1. 物理锁定 1.pdf
        stmt_doc = select(Document).where(Document.filename == '1.pdf').order_by(Document.created_at.desc()).limit(1)
        doc_record = (await session.execute(stmt_doc)).scalar_one_or_none()
        
        if not doc_record:
            console.print("[red]❌ 数据库中未找到 1.pdf 记录。[/red]")
            return

        # 2. 获取已确权的脊梁 (TOC)
        stmt_toc = select(TocItem).where(TocItem.document_id == doc_record.id).order_by(TocItem.physical_start)
        tocs_db = (await session.execute(stmt_toc)).scalars().all()
        console.print(f"📖 逻辑脊梁已就绪：{len(tocs_db)} 个节点。")

        # 3. 物理清空旧 Chunk
        console.print(f"🧹 正在清空 {doc_record.filename} 的旧语义分片...")
        await session.execute(delete(Chunk).where(Chunk.document_id == doc_record.id))
        await session.commit()

        # 4. 执行全量 OCR 收割 (GPU + 并发锁 + 50页断点)
        console.print(f"📸 [Pipeline] 启动 406 页满血收割流水线...")
        
        # 物理删除残缺缓存，强制重绘
        cache_path = PROJECT_ROOT / "ceshi_ocr" / "1.pdf.ocr_cache.json"
        if cache_path.exists():
            console.print(f"🗑️ 已删除残缺缓存: {cache_path}")
            cache_path.unlink()

        raw_toc_dicts = [{"page": t.page, "title": t.title, "logical_page": t.page} for t in tocs_db]
        
        _, page_markdowns = await alchemist.run_full_pipeline(
            str(PROJECT_ROOT / "ceshi_ocr" / "1.pdf"),
            raw_toc_dicts,
            doc_record.total_pages,
            force_ocr=True 
        )

        # 5. 执行逻辑重组
        console.print(f"🧩 [Pipeline] OCR 收割完成，执行语义合龙与打标...")
        spine_nodes = [SpineNode(
            id=t.id, title=t.title, level=t.level, 
            logical_page=t.page, physical_start=t.physical_start, physical_end=t.physical_end
        ) for t in tocs_db]

        raw_segments = []
        with fitz.open(str(PROJECT_ROOT / "ceshi_ocr" / "1.pdf")) as pdf_doc:
            async for seg in structural_splitter.split_by_toc(pdf_doc, spine_nodes, ocr_context=page_markdowns):
                raw_segments.append(seg)

        # 6. 语义精炼与 KeyBERT
        console.print(f"💎 [Pipeline] 注入 1024 维语义指纹与 LogicTags...")
        refined_chunks = await refiner.refine_batch(doc_record.filename, spine_nodes, raw_segments)

        # 7. 终极持久化
        console.print(f"💾 [Pipeline] 持久化 {len(refined_chunks)} 个高质量分片到数据库...")
        for c in refined_chunks:
            session.add(Chunk(
                id=UUID(c["id"]), content=c["content"], page_number=c["page_number"],
                breadcrumb=c["breadcrumb"], document_id=doc_record.id,
                embedding=c["embedding"], logic_tags=c["logic_tags"],
                metadata_json=c["metadata_json"], toc_item_id=UUID(c["metadata_json"]["toc_item_id"]) if "toc_item_id" in c["metadata_json"] else None
            ))
        
        await session.commit()
        console.print(f"\n[bold green]✅ [Success] 1.pdf 全量入库完成！逻辑原材料现已达生产级。[/bold green]")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(ingest_fast_track())
