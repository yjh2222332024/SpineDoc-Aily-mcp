
import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

# 路径对齐
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.db import get_async_sessionmaker
from sqlmodel import select
from app.core.models import Document, TocItem, Chunk

console = Console()

async def inspect_paper_quality():
    console.print(Panel("[bold cyan]🧭 SpineDoc 全量知识资产质量巡检 (V31.0)[/bold cyan]"))
    
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        # 1. 获取所有已完成的文档
        stmt = select(Document).order_by(Document.created_at.desc())
        docs = (await session.execute(stmt)).scalars().all()
        
        if not docs:
            console.print("[yellow]库中空空如也，请先运行 ingest。[/yellow]")
            return

        for doc in docs:
            # 获取文档关联的 TOC 项
            toc_stmt = select(TocItem).where(TocItem.document_id == doc.id).order_by(TocItem.page.asc())
            toc_items = (await session.execute(toc_stmt)).scalars().all()
            
            # 获取文档的部分关键词（从 Chunk 中采样）
            chunk_stmt = select(Chunk).where(Chunk.document_id == doc.id).limit(20)
            chunks = (await session.execute(chunk_stmt)).scalars().all()
            
            # 聚合关键词
            all_kws = set()
            for c in chunks:
                if c.metadata_json and "keywords" in c.metadata_json:
                    all_kws.update(c.metadata_json["keywords"])
            
            # 渲染文档面板
            doc_info = f"[bold white]文件名:[/] {doc.filename}\n[bold white]ID:[/] {str(doc.id)[:8]}\n[bold white]总页数:[/] {doc.total_pages}\n[bold white]核心领域词:[/] {', '.join(list(all_kws)[:15])}"
            console.print(Panel(doc_info, title=f"📄 文档档案", border_style="green"))

            # 渲染逻辑脊梁表
            table = Table(title="🧠 逻辑脊梁与章节精要", show_header=True, header_style="bold magenta", box=None)
            table.add_column("页码", style="dim", width=6)
            table.add_column("层级", justify="center")
            table.add_column("章节标题", style="bold yellow", width=30)
            table.add_column("AI 逻辑摘要 (Contextual Summary)", style="italic green")

            for it in toc_items[:25]: # 仅显示前 25 项以保持简洁
                # 尝试从 Chunk 的 metadata 中找该章节的 summary (因为我们在 Ingest 时同步写进去了)
                summary = "正在分析中..."
                # 寻找匹配该章节 ID 的第一个 chunk
                for c in chunks:
                    if c.metadata_json.get("toc_item_id") == str(it.id):
                        summary = c.metadata_json.get("chapter_summary", "正文详细讨论章节。")
                        break
                
                prefix = "  " * (it.level - 1)
                table.add_row(
                    f"P{it.page}",
                    str(it.level),
                    f"{prefix}{it.title}",
                    summary
                )
            
            console.print(table)
            if len(toc_items) > 25:
                console.print(f"[dim]... 还有 {len(toc_items)-25} 个子章节已收录[/dim]")
            console.print("\n" + "="*100 + "\n")

if __name__ == "__main__":
    asyncio.run(inspect_paper_quality())
