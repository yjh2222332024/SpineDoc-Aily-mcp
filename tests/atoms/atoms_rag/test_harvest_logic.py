import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

# 🏛️ 顶级架构锚定
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.app.services.rag.vector_store import PostgresStore
from backend.app.services.rag.pyramid_harvester import PyramidHarvester
from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document
from sqlalchemy import select

console = Console()

async def run_pyramid_test():
    console.print("[bold cyan]🧪 [Atomic-Pyramid] 启动金字塔巡航压力测试...[/bold cyan]")
    
    store = PostgresStore()
    harvester = PyramidHarvester(store)
    
    # 1. 自动锁定样本
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        stmt = select(Document).where(Document.filename == '1.pdf').order_by(Document.created_at.desc()).limit(1)
        doc = (await session.execute(stmt)).scalar_one_or_none()
        if not doc:
            console.print("[red]❌ 未找到 1.pdf。[/red]")
            return
        doc_id = str(doc.id)

    # 2. 定义测试查询：SM4 的数学基础
    # 这个查询在逻辑上属于“分组密码” -> “SM4”
    query = "SM4 算法的数学基础与可逆性分析"
    
    console.print(f"🔍 [Query]: {query}\n")

    # 3. 执行金字塔收割
    results = await harvester.harvest(
        query=query, 
        doc_id=doc_id, 
        limit=10
    )

    # 4. 展示收割清单
    table = Table(title="Pyramid Navigation Evidence Report", show_lines=True, header_style="bold white on blue")
    table.add_column("Rank", justify="center")
    table.add_column("Score", style="cyan")
    table.add_column("Page", justify="center")
    table.add_column("Source Signals", style="yellow")
    table.add_column("Logic Path", style="green")
    table.add_column("Content Snippet", width=60)

    for i, res in enumerate(results, 1):
        signals = []
        if res.get("found_by_lane_vec"): signals.append("📡 Lane-Vec")
        if res.get("found_by_lane_tag"): signals.append("🏷️ Lane-Tag")
        if res.get("found_by_global_vec"): signals.append("🌎 Global-Vec")
        if res.get("in_pyramid_lane"): signals.append("🚀 Pyramid-Lane")
        if res.get("path_aware"): signals.append("🧠 Path-Match")

        table.add_row(
            str(i),
            f"{res.get('rrf_score', 0):.4f}",
            f"P{res.get('page_number', 0)}",
            "\n".join(signals),
            str(res.get("breadcrumb", "N/A")),
            res.get("content", "")[:150].replace("\n", " ") + "..."
        )

    console.print(table)

    if results:
        console.print("\n[bold green]✅ [Verdict] 金字塔巡航验证结束。[/bold green]")
    else:
        console.print("\n[bold red]❌ [Verdict] 未召回任何有效证据。[/bold red]")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_pyramid_test())
