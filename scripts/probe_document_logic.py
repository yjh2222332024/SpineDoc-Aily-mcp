import asyncio
import sys
from pathlib import Path
from uuid import UUID
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# 🏛️ 顶级架构锚定
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, Chunk
from sqlalchemy import select

console = Console()

async def list_all_details():
    console.print("[bold cyan]📡 [Probe] 正在采样前 30 个分片详情...[/bold cyan]")
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        # 1. 锁定目标文档
        stmt_doc = select(Document).order_by(Document.created_at.desc()).limit(1)
        doc = (await session.execute(stmt_doc)).scalar_one_or_none()
        
        if not doc:
            console.print("[bold red]❌ 未找到任何处理记录。[/bold red]")
            return

        console.print(f"[green]✅ 目标文档: {doc.filename} (ID: {str(doc.id)[:8]})[/green]\n")

        # 2. 提取分片 (Limit 30)
        stmt_chunks = select(Chunk).where(Chunk.document_id == doc.id).order_by(Chunk.page_number, Chunk.id).limit(30)
        chunks = (await session.execute(stmt_chunks)).scalars().all()

        for i, c in enumerate(chunks, 1):
            # 构造信息头部
            info_header = Text()
            info_header.append("Index: ", style="bold yellow")
            info_header.append(f"{i}/{len(chunks)} | ")
            info_header.append("Physical Page: ", style="bold yellow")
            info_header.append(f"P{c.page_number}\n")
            info_header.append("Breadcrumb: ", style="bold yellow")
            info_header.append(f"{c.breadcrumb}\n", style="italic green")
            info_header.append("Logic Tags: ", style="bold yellow")
            info_header.append(f"{', '.join(c.logic_tags)}\n", style="cyan")
            info_header.append("─" * 60, style="dim")

            # 组合内容
            full_content = Text.assemble(info_header, "\n\n", Text(c.content))

            # 展示面板
            console.print(Panel(
                full_content,
                title=f"Segment #{i}",
                border_style="bright_blue",
                padding=(1, 2)
            ))
            console.print("") 

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(list_all_details())
