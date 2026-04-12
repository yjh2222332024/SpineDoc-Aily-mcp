
import asyncio
import sys
import re
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# 路径对齐
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.db import get_async_sessionmaker
from sqlmodel import select
from app.core.models import Chunk, Document

console = Console()

async def show_gallery():
    console.print(Panel("[bold yellow]🔍 V26.1 专家关键词与分块质量画廊[/bold yellow]"))
    
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        # 获取 1.pdf 的最新 doc_id
        doc_stmt = select(Document).where(Document.filename == '1.pdf').order_by(Document.created_at.desc())
        doc = (await session.execute(doc_stmt)).scalars().first()
        
        if not doc:
            console.print("[red]❌ 未找到 1.pdf 的数据，请先运行 Ingest。[/red]")
            return

        # 选取前 8 个分块
        stmt = select(Chunk).where(Chunk.document_id == doc.id).limit(8)
        res = await session.execute(stmt)
        chunks = res.scalars().all()
        
        for i, c in enumerate(chunks):
            # 提取头部关键词标签
            kw_match = re.search(r"【关键词: (.*?)】", c.content)
            keywords = kw_match.group(1) if kw_match else "N/A"
            # 去除标签后的纯净内容预览
            clean_content = c.content.split("】")[-1].strip()[:250] + "..."
            
            # 🚀 修正后的渲染
            table = Table(show_header=False, border_style="dim", box=None)
            table.add_row("[bold magenta]物理页码:[/bold magenta]", f"P{c.page_number}")
            table.add_row("[bold green]逻辑路径:[/bold green]", c.breadcrumb)
            table.add_row("[bold cyan]Jieba 标签:[/bold cyan]", Text(keywords, style="bold yellow"))
            
            console.print(Panel(
                table, 
                title=f"分块 #{i+1} [ID: {str(c.id)[:8]}]", 
                border_style="blue"
            ))
            console.print(Text(clean_content, style="italic dim"))
            console.print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    asyncio.run(show_gallery())
