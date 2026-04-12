
import asyncio
import sys
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

# 路径对齐
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from spine_cli.core.engine import SpineEngine
from app.core.db import get_async_sessionmaker
from sqlmodel import select
from app.core.models import Chunk, Document

console = Console()

async def test_50p_extraction():
    console.print(Panel("[bold cyan]🧪 SpineDoc V26.1 数字化质量采样 (前50页定制版)[/bold cyan]"))
    
    engine = SpineEngine()
    file_path = "ocr_ceshi/1.pdf"
    
    # 1. 强制重置（调用我们之前的脚本逻辑）
    from scripts.force_reset_doc import force_reset
    await force_reset()
    
    # 2. 启动受限 Ingest
    start_time = time.time()
    console.print(f"🚀 [Ingest] 正在启动 4060 动力收割，目标：[bold]前 50 页[/bold]...")
    
    # 注入前 50 页限制
    doc_id = await engine.ingest_document(
        file_path, 
        manual_toc_range=list(range(9, 15)), # 假设目录还在这个范围
        limit_pages=50,
        progress_callback=lambda m: console.print(f"  > [dim]{m}[/dim]")
    )
    
    duration = time.time() - start_time
    console.print(f"\n✅ [Done] 50页数字化完成，总耗时: [bold green]{duration:.2f}s[/bold green]\n")

    # 3. 抽样检查关键词与分块质量
    console.print(Panel("[bold yellow]🔍 语义标签与分词画廊 (抽样结果)[/bold yellow]"))
    
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        # 选取前 5 个分块
        stmt = select(Chunk).where(Chunk.document_id == doc_id).limit(8)
        res = await session.execute(stmt)
        chunks = res.scalars().all()
        
        for i, c in enumerate(chunks):
            # 提取头部关键词标签
            kw_match = re.search(r"【关键词: (.*?)】", c.content)
            keywords = kw_match.group(1) if kw_match else "N/A"
            clean_content = c.content.split("】")[-1].strip()[:200] + "..."
            
            # 渲染卡片
            table = Table(show_header=False, border_style="dim", box=None)
            table.add_row("[bold magenta]页码:[/bold magenta]", f"P{c.page_number}")
            table.add_row("[bold green]路径:[/bold magenta]", c.breadcrumb)
            table.add_row("[bold cyan]V26.1 标签:[/bold cyan]", Text(keywords, style="bold yellow"))
            
            console.print(Panel(
                table, 
                title=f"分块 #{i+1} [ID: {str(c.id)[:8]}]", 
                border_style="blue"
            ))
            console.print(Text(clean_content, style="italic dim"))
            console.print("-" * 60)

import re
if __name__ == "__main__":
    asyncio.run(test_50p_extraction())
