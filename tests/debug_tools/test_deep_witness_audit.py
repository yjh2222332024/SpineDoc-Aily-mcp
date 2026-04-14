"""
SpineDoc 长文档智能体压测脚本 (Operation: Deep Water)
======================================================
目标：针对 406 页巨著 (1.pdf) 验证 WitnessGraph 的深度导航与量化精度。
"""
import asyncio
import sys
import json
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# 🏛️ 路径锚定
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.intelligence.witness.graph import witness_graph
from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem
from sqlmodel import select

console = Console()

async def run_deep_audit():
    console.print("[bold magenta]🧪 [Deep-Audit] 启动 406 页长文档压力测试...[/bold magenta]")
    
    # 1. 自动锁定 1.pdf
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        stmt = select(Document).where(Document.filename == '1.pdf').order_by(Document.created_at.desc()).limit(1)
        doc = (await session.execute(stmt)).scalar_one_or_none()
        if not doc:
            console.print("[red]❌ 未找到 1.pdf。请先完成入库。[/red]")
            return
        
        # 提取全量 TOC（模拟真实环境）
        stmt_toc = select(TocItem).where(TocItem.document_id == doc.id)
        tocs = (await session.execute(stmt_toc)).scalars().all()
        toc_list = [{"title": t.title, "level": t.level, "p": t.physical_start} for t in tocs]

    # 2. 定义高难度审计问题
    query = "文中详细描述的 SM2 数字签名算法的生成步骤有哪些？请严格引用原文公式。"
    
    initial_state = {
        "query": query,
        "doc_id": str(doc.id),
        "toc": toc_list,
        "sub_queries": [],
        "fingerprint_pool": [],
        "selected_ids": [],
        "pro_evidence": [],
        "citation_ids": [],
        "is_sufficient": False,
        "final_answer": ""
    }

    console.print(f"🔍 [Query]: {query}\n")

    # 3. 运行并计时
    start_time = time.time()
    final_output = await witness_graph.ainvoke(initial_state)
    end_time = time.time()

    # 4. 展示量化指标
    duration = end_time - start_time
    citation_count = len(final_output.get('citation_ids', []))
    
    metric_table = Table(title="📊 Witness Intelligence 量化审计报告")
    metric_table.add_column("指标", style="cyan")
    metric_table.add_column("数值", style="green")
    
    metric_table.add_row("总耗时 (Latency)", f"{duration:.2f}s")
    metric_table.add_row("侦察任务数 (Fan-out)", str(len(final_output.get('sub_queries', []))))
    metric_table.add_row("指纹收割数 (Recall)", str(len(final_output.get('fingerprint_pool', []))))
    metric_table.add_row("质证通过数 (Verified)", str(citation_count))
    metric_table.add_row("逻辑覆盖率 (Spine-Coverage)", f"{(len(final_output.get('sub_queries', []))/3)*100:.0f}%")
    
    console.print(metric_table)

    # 5. 展示结论
    console.print(Panel(
        f"{final_output['final_answer']}",
        title="👨‍⚖️ 单文档证词 (1.pdf)",
        border_style="cyan"
    ))

    # 6. 核心验证断言
    # SM2 签名算法在 1.pdf 中通常在 P219 左右
    target_page = 219
    cited_pages = [e['page'] for e in final_output.get('pro_evidence', [])]
    
    hit_core = any(abs(p - target_page) <= 2 for p in cited_pages)
    
    if hit_core:
        console.print(f"\n[bold green]✅ [Verdict] 深度审计大获全胜！精准命中 P219 SM2 核心逻辑区。[/bold green]")
    else:
        console.print(f"\n[bold red]❌ [Verdict] 深度审计失败。引用页码: {cited_pages}，偏离了核心逻辑区 P219。[/bold red]")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_deep_audit())
