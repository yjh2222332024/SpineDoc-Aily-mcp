import asyncio
import sys
import os
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

async def run_full_recall_test():
    console.print("[bold cyan]🧪 [Atomic-Forensic] 启动 406 页全量文档检索压力测试...[/bold cyan]")
    
    store = PostgresStore()
    harvester = PyramidHarvester(store)
    
    # 1. 自动锁定最新全量版 1.pdf
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        stmt = select(Document).where(Document.filename == '1.pdf').order_by(Document.created_at.desc()).limit(1)
        doc = (await session.execute(stmt)).scalar_one_or_none()
        if not doc:
            console.print("[red]❌ 未找到 1.pdf。[/red]")
            return
        doc_id = str(doc.id)

    # 2. 定义高难度硬核查询
    # 这个查询专门考察系统对“签名”vs“加密”的区分能力（两者都在书中大量出现）
    query = "SM2 数字签名算法的具体签名生成步骤与对应的数学计算公式"
    console.print(f"🔍 [Query]: {query}\n")

    # 3. 执行金字塔收割 (V3.1 自适应版)
    results = await harvester.harvest(query=query, doc_id=doc_id, limit=5)

    # 4. 展示法医级证据报告
    table = Table(title="406-Page Full Document Evidence Audit", show_lines=True, header_style="bold white on magenta")
    table.add_column("Rank", justify="center")
    table.add_column("Score", style="cyan")
    table.add_column("Phys-Page", justify="center")
    table.add_column("Logic Path (Breadcrumb)", style="green")
    table.add_column("Evidence Tags", style="yellow")
    table.add_column("Evidence Snippet", width=80)

    for i, res in enumerate(results, 1):
        tags = res.get("logic_tags", [])
        tag_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
        
        table.add_row(
            str(i),
            f"{res.get('rrf_score', 0):.4f}",
            f"P{res.get('page_number', 0)}",
            str(res.get("breadcrumb", "N/A")),
            tag_str[:40] + "...",
            res.get("content", "").replace("\n", " ")[:200] + "..."
        )

    console.print(table)

    # 5. 自动判定：SM2 签名算法在书中大约位于 P219 之后
    target_pages = range(218, 225)
    if results and results[0].get("page_number") in target_pages:
        console.print(f"\n[bold green]✅ [Verdict] 完美收官！首位证据命中物理页 P{results[0].get('page_number')}，属于 SM2 签名核心区域。[/bold green]")
    else:
        console.print(f"\n[bold red]❌ [Verdict] 检索发生逻辑漂移。首位证据命中 P{results[0].get('page_number') if results else 'None'}，未能锁定 P219 附近的核心步骤。[/bold red]")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_full_recall_test())
