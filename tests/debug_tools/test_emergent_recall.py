"""
SpineDoc 专项测试：逻辑涌现检索验证 (V3.5)
===========================================
测试目标：验证在没有任何原始目录的情况下，合成脊梁是否能有效引导金字塔检索。
"""
import asyncio
import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table

# 🏛️ 路径锚定
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.rag.vector_store import PostgresStore
from backend.app.services.rag.pyramid_harvester import PyramidHarvester
from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document
from sqlalchemy import select

console = Console()

async def run_emergent_recall_test():
    console.print("[bold cyan]🧪 [Emergent-Recall] 启动逻辑涌现检索测试...[/bold cyan]")
    
    store = PostgresStore()
    harvester = PyramidHarvester(store)
    
    # 1. 自动锁定逻辑涌现的样本 (2401.08406v3.pdf)
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        stmt = select(Document).where(Document.filename == '2401.08406v3.pdf').order_by(Document.created_at.desc()).limit(1)
        doc = (await session.execute(stmt)).scalar_one_or_none()
        if not doc:
            console.print("[red]❌ 未找到逻辑涌现文档样本。请先运行 test_emergent_spine_pipeline.py[/red]")
            return
        doc_id = str(doc.id)

    # 2. 定义针对性的学术查询
    query = "文中提到的 RAG 相比 Fine-tuning 的主要优势和局限性是什么？"
    console.print(f"🔍 [Query]: {query}\n")

    # 3. 执行金字塔收割
    results = await harvester.harvest(query=query, doc_id=doc_id, limit=5)

    # 4. 展示收割报告
    table = Table(title="Emergent Spine Navigation Audit", show_lines=True)
    table.add_column("Rank", justify="center")
    table.add_column("Score", style="cyan")
    table.add_column("Phys-Page", justify="center")
    table.add_column("Synthetic Path (涌现路径)", style="green")
    table.add_column("Content Snippet", width=80)

    for i, res in enumerate(results, 1):
        table.add_row(
            str(i),
            f"{res.get('rrf_score', 0):.4f}",
            f"P{res.get('page_number', 0)}",
            str(res.get("breadcrumb", "N/A")),
            res.get("content", "").replace("\n", " ")[:200] + "..."
        )

    console.print(table)

    # 5. 自动判定：该问题的答案核心在 P29 (Table 23 附近)
    target_pages = range(28, 31)
    if results and results[0].get("page_number") in target_pages:
        console.print(f"\n[bold green]✅ [Verdict] 检索大捷！首位证据命中 P{results[0].get('page_number')}，路径为：{results[0].get('breadcrumb')}。[/bold green]")
        console.print("[dim]这证明了合成脊梁在导航主权上的有效性。[/dim]")
    else:
        console.print(f"\n[bold red]❌ [Verdict] 检索漂移。首位证据命中 P{results[0].get('page_number') if results else 'None'}。[/bold red]")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_emergent_recall_test())
