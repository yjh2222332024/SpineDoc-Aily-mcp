import asyncio
import sys
import json
import time
import fitz
from pathlib import Path
from rich.console import Console
from rich.progress import Progress
from sqlalchemy import select, delete, text
from uuid import UUID

# 🏛️ 顶级架构锚定
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem, Chunk
from backend.app.services.rag.vector_store import PostgresStore
from backend.app.services.ingestion.splitter import structural_splitter
from backend.app.services.ingestion.logic_refiner import LogicRefiner
from backend.app.services.toc.base import SpineNode

console = Console()

async def reassemble_production_standard():
    console.print("[bold cyan]🔄 [Re-Assembly] 启动生产级逻辑重整 (复刻 Ingest 流程)...[/bold cyan]")
    
    session_maker = get_async_sessionmaker()
    store = PostgresStore()
    refiner = LogicRefiner(threshold=0.25) # 生产级参数
    
    async with session_maker() as session:
        # 1. 锁定 1.pdf 及其 TOC 脊梁
        stmt_doc = select(Document).where(Document.filename == '1.pdf').order_by(Document.created_at.desc()).limit(1)
        doc_record = (await session.execute(stmt_doc)).scalar_one_or_none()
        
        if not doc_record:
            console.print("[red]❌ 数据库中未找到 1.pdf 记录。[/red]")
            return

        stmt_toc = select(TocItem).where(TocItem.document_id == doc_record.id).order_by(TocItem.physical_start)
        toc_items_db = (await session.execute(stmt_toc)).scalars().all()
        
        # 转换为 Splitter 需要的 SpineNode 对象
        spine_nodes = [SpineNode(
            id=t.id, title=t.title, level=t.level, 
            logical_page=t.page, physical_start=t.physical_start, physical_end=t.physical_end
        ) for t in toc_items_db]
        
        console.print(f"📖 已加载脊梁：{len(spine_nodes)} 个章节节点。")

        # 2. 加载磁盘存档
        cache_path = Path(f"ceshi_ocr/1.pdf.ocr_cache.json")
        if not cache_path.exists():
            console.print(f"[red]❌ 缓存不存在: {cache_path}[/red]")
            return
            
        with open(cache_path, 'r', encoding='utf-8') as f:
            ocr_raw = json.load(f)
            # 物理页码映射：SpineDoc 内部使用 0-based page_idx 作为 key
            ocr_context = {int(k): v for k, v in ocr_raw.items()}

        # 3. 物理清空旧分片 (强制确权)
        console.print(f"🧹 物理清空 {doc_record.filename} 的旧分片数据...")
        await session.execute(delete(Chunk).where(Chunk.document_id == doc_record.id))
        await session.commit()

        # 4. 执行结构化分片 (调用生产版 structural_splitter)
        raw_segments = []
        start_time = time.time()
        
        # 为了兼容 split_by_toc，我们需要打开 PDF 句柄（仅用于获取页数）
        pdf_file = PROJECT_ROOT / "ceshi_ocr" / "1.pdf"
        with fitz.open(str(pdf_file)) as pdf_doc:
            async for seg in structural_splitter.split_by_toc(pdf_doc, spine_nodes, ocr_context=ocr_context):
                raw_segments.append(seg)

        # 5. 逻辑精炼与指纹注入 (LogicRefiner)
        console.print(f"💎 正在进行语义精炼与 KeyBERT 打标 ({len(raw_segments)} 个分片)...")
        refined_chunks = await refiner.refine_batch(doc_record.filename, spine_nodes, raw_segments)

        # 6. 批量持久化 (GPU 加速)
        console.print(f"📥 正在持久化最终知识库...")
        for c in refined_chunks:
            chunk_obj = Chunk(
                id=UUID(c["id"]),
                content=c["content"],
                page_number=c["page_number"],
                breadcrumb=c["breadcrumb"],
                document_id=doc_record.id,
                embedding=c["embedding"],
                logic_tags=c["logic_tags"],
                metadata_json=c["metadata_json"]
            )
            session.add(chunk_obj)
            
        await session.commit()
        
        elapsed = time.time() - start_time
        console.print(f"\n[bold green]✅ [Success] 1.pdf 全量逻辑重组完成！[/bold green]")
        console.print(f"📊 统计：耗时 {elapsed:.2f}s | 生成分片: {len(refined_chunks)}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(reassemble_production_standard())
