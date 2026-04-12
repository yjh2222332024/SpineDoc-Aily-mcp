
import asyncio
import sys
import json
import re
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# 路径对齐
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.db import get_async_sessionmaker
from sqlmodel import select
from app.core.models import Chunk, Document

console = Console()

async def inspect_chunks():
    console.print(Panel("[bold green]🏟️ SpineDoc V31.0 知识切片质量巡检[/bold green]"))
    
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        # 获取最新处理的文档
        doc_stmt = select(Document).order_by(Document.created_at.desc())
        doc = (await session.execute(doc_stmt)).scalars().first()
        
        if not doc:
            console.print("[red]❌ 库中无数据[/red]")
            return

        console.print(f"🎯 [Target] 文档: [bold cyan]{doc.filename}[/bold cyan] (ID: {str(doc.id)[:8]})")

        # 抽样 3 个分块，涵盖不同的章节
        chunk_stmt = select(Chunk).where(Chunk.document_id == doc.id).limit(3)
        chunks = (await session.execute(chunk_stmt)).scalars().all()
        
        for i, c in enumerate(chunks):
            content = c.content
            
            # 🚀 深度解析结构化标签
            kw_match = re.search(r"【关键词: (.*?)】", content)
            bg_match = re.search(r"【文档背景: (.*?)】", content)
            sm_match = re.search(r"【本章核心精要: (.*?)】", content)
            
            keywords = kw_match.group(1) if kw_match else "N/A"
            background = bg_match.group(1) if bg_match else "N/A"
            summary = sm_match.group(1) if sm_match else "N/A"
            
            # 截取纯正文
            body_text = content.split("】")[-1].strip()[:400] + "..."
            
            # 渲染精美报告
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_row("[bold yellow]🏷️ 专家关键词:[/]", keywords)
            table.add_row("[bold blue]🌍 文档背景:[/]", background)
            table.add_row("[bold magenta]💡 章节精要:[/]", f"[italic]{summary}[/]")
            table.add_row("[bold cyan]📍 物理页码:[/]", f"P{c.page_number}")
            table.add_row("[bold green]🌿 逻辑脊梁:[/]", c.breadcrumb)
            
            console.print(Panel(
                table, 
                title=f"精英切片 #{i+1} [ID: {str(c.id)[:8]}]", 
                border_style="bright_blue"
            ))
            console.print(f"[dim]{body_text}[/dim]\n" + "="*80)

if __name__ == "__main__":
    asyncio.run(inspect_chunks())
