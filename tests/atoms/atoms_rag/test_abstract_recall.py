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

async def run_abstract_test():
    console.print("[bold cyan]🧪 [Atomic-Abstract] 启动“广角探测”压力测试...[/bold cyan]")
    
    store = PostgresStore()
    harvester = PyramidHarvester(store)
    
    # 1. 锁定文档
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        stmt = select(Document).where(Document.filename == '1.pdf').order_by(Document.created_at.desc()).limit(1)
        doc = (await session.execute(stmt)).scalar_one_or_none()
        if not doc:
            console.print("[red]❌ 未找到目标文档。[/red]")
            return
        doc_id = str(doc.id)

    # 2. 抽象查询：考察系统对全书 SM 系列算法的跨章搜寻能力
    query = "总结本书中提到的中国商用密码算法（SM系列）及其在对称加密、公钥密码、杂凑函数中的布局"
    console.print(f"🔍 [Abstract Query]: {query}\n")

    # 3. 执行金字塔收割
    results = await harvester.harvest(query=query, doc_id=doc_id, limit=10)

    # 4. 展示报告
    table = Table(title="Abstract Query: Evidence Diversity Audit", show_lines=True)
    table.add_column("Rank", justify="center")
    table.add_column("Page", justify="center")
    table.add_column("Chapter / Path", style="green")
    table.add_column("Confidence Signal", style="yellow")
    table.add_column("Snippet Preview", width=70)

    found_chapters = set()
    for i, res in enumerate(results, 1):
        path = str(res.get("breadcrumb", "N/A"))
        found_chapters.add(path)
        
        signal = "🌎 Global"
        if res.get("in_pyramid_lane"): signal = "🚀 Lane-Boost"
        if res.get("path_aware"): signal += " + 🧠 Path"

        table.add_row(
            str(i),
            f"P{res.get('page_number', 0)}",
            path[:40],
            signal,
            res.get("content", "").replace("\n", " ")[:120] + "..."
        )

    console.print(table)

    # 5. 法医判定
    console.print(f"\n📊 证据集散度：从 {len(found_chapters)} 个逻辑章节召回了证据。")
    if len(found_chapters) >= 3:
        console.print("[bold green]✅ [Verdict] 测试通过：系统成功克服了“信息孤岛”，完成了跨章逻辑收割。[/bold green]")
    else:
        console.print("[bold red]❌ [Verdict] 测试失败：检索结果过于单一，未能捕捉到全书的 SM 算法布局。[/bold red]")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_abstract_test())
