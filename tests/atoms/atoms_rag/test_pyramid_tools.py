import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

# 🏛️ 顶级架构锚定
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.app.services.rag.vector_store import PostgresStore # 🚀 更新导入
from backend.app.services.rag.evidence_harvester import EvidenceHarvester
from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem
from sqlalchemy import select

console = Console()

async def run_pyramid_tool_test():
    console.print("[bold cyan]🧪 [Atomic-Pyramid] 验证金字塔物理航道解析器...[/bold cyan]")
    
    store = PostgresStore()
    
    # 1. 自动锁定 1.pdf 及其 TOC 项
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        # 获取 1.pdf 的最新 ID
        stmt_doc = select(Document).where(Document.filename == '1.pdf').order_by(Document.created_at.desc()).limit(1)
        doc = (await session.execute(stmt_doc)).scalar_one_or_none()
        if not doc:
            console.print("[red]❌ 未找到 1.pdf 样本。[/red]")
            return
        
        # 随机抽取 3 个 TOC 项
        stmt_toc = select(TocItem).where(TocItem.document_id == doc.id).limit(3)
        tocs = (await session.execute(stmt_toc)).scalars().all()
        toc_ids = [t.id for t in tocs]
        
        console.print(f"📡 采样到 {len(tocs)} 个章节标题: {[t.title for t in tocs]}")

    # 2. 调用原子工具
    ranges = await store.get_toc_ranges_by_ids(toc_ids)
    
    # 3. 展示结果
    table = Table(title="Pyramid Lane Resolution Audit")
    table.add_column("Chapter", style="green")
    table.add_column("Physical Range", style="cyan")
    
    for t, r in zip(tocs, ranges):
        table.add_row(t.title, f"P{r[0]} - P{r[1]}")
    
    console.print(table)

    if len(ranges) == len(toc_ids):
        console.print("\n[bold green]✅ [Verdict] 物理航道解析原子验证通过。[/bold green]")
    else:
        console.print("\n[bold red]❌ [Verdict] 物理航道解析失败：结果数量不匹配。[/bold red]")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_pyramid_tool_test())
