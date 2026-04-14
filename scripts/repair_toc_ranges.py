import asyncio
import sys
from pathlib import Path
from uuid import UUID
from rich.console import Console
from rich.table import Table

# 🏛️ 顶级架构锚定
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem
from sqlalchemy import select

console = Console()

async def repair_toc():
    console.print("[bold cyan]🔧 [Repair] 正在启动 TOC 物理区间修复程序...[/bold cyan]")
    session_maker = get_async_sessionmaker()
    
    async with session_maker() as session:
        # 1. 锁定最新的 1.pdf
        stmt_doc = select(Document).where(Document.filename == '1.pdf').order_by(Document.created_at.desc()).limit(1)
        doc = (await session.execute(stmt_doc)).scalar_one_or_none()
        
        if not doc:
            console.print("[red]❌ 未找到 1.pdf 处理记录。[/red]")
            return

        total_pages = doc.total_pages
        console.print(f"📖 目标文档: {doc.filename} | 总页数: {total_pages}")

        # 2. 加载所有 TOC 项
        stmt_toc = select(TocItem).where(TocItem.document_id == doc.id).order_by(TocItem.physical_start)
        tocs = (await session.execute(stmt_toc)).scalars().all()
        
        if not tocs:
            console.print("[yellow]⚠️ 该文档没有目录项。[/yellow]")
            return

        # 3. 应用最新闭合算法
        stack = []
        for current in tocs:
            while stack and stack[-1].level >= current.level:
                closed = stack.pop()
                if current.physical_start > closed.physical_start:
                    closed.physical_end = current.physical_start - 1
                else:
                    closed.physical_end = current.physical_start
            
            stack.append(current)
            
        while stack:
            remaining = stack.pop()
            remaining.physical_end = total_pages

        # 4. 展示前 20 条修复结果
        table = Table(title=f"Repair Audit (Top 20 Nodes)")
        table.add_column("Title", style="green")
        table.add_column("Level", justify="center")
        table.add_column("Physical Range", style="bold cyan")

        for t in tocs[:20]:
            table.add_row(t.title[:40], str(t.level), f"P{t.physical_start} - P{t.physical_end}")
            session.add(t)

        console.print(table)

        # 5. 强制执行持久化 (自动模式)
        console.print(f"\n🚀 正在同步 {len(tocs)} 个节点的物理疆域到数据库...")
        await session.commit()
        console.print("[bold green]✅ [Success] 数据库 TOC 物理区间已全量校准。[/bold green]")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(repair_toc())
