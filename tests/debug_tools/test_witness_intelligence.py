"""
SpineDoc 证人智能体压力测试 (Operation: Smart Witness)
======================================================
测试目标：验证 WitnessGraph 是否能通过“意图拆解”和“逻辑质证”解决检索漂移。
"""
import asyncio
import sys
import json
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

# 🏛️ 路径锚定
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.intelligence.witness.graph import witness_graph
from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem
from sqlmodel import select

console = Console()

async def test_witness_intelligence():
    console.print("[bold cyan]🧪 [Witness-Intelligence] 启动单文档证人压力测试...[/bold cyan]")
    
    # 1. 自动锁定测试样本 (2401.08406v3.pdf)
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        stmt = select(Document).where(Document.filename == '2401.08406v3.pdf').order_by(Document.created_at.desc()).limit(1)
        doc = (await session.execute(stmt)).scalar_one_or_none()
        if not doc:
            console.print("[red]❌ 未找到文档样本。[/red]")
            return
        
        # 提取 TOC 给 Agent 参考
        stmt_toc = select(TocItem).where(TocItem.document_id == doc.id)
        tocs = (await session.execute(stmt_toc)).scalars().all()
        toc_list = [{"title": t.title, "level": t.level, "p": t.physical_start} for t in tocs]

    # 2. 构造初始状态
    initial_state = {
        "query": "文中提到的 RAG 相比 Fine-tuning 的主要优势和局限性是什么？",
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

    console.print(f"🔍 [Query]: {initial_state['query']}\n")

    # 3. 运行 LangGraph
    final_output = await witness_graph.ainvoke(initial_state)

    # 4. 展示质证成果
    console.print(Panel(f"[bold green]Scout 拆解任务:[/bold green]\n{json.dumps(final_output['sub_queries'], indent=2, ensure_ascii=False)}"))
    
    console.print(f"\n⚖️ [Examiner] 质证员锁定的分片数量: {len(final_output['selected_ids'])}")
    
    console.print(Panel(
        f"[bold blue]👨‍⚖️ 最终证词 (Final Testimony):[/bold blue]\n\n{final_output['final_answer']}",
        title="SpineDoc 3.5 判决书",
        border_style="magenta"
    ))

    # 5. 自动验证
    if "(P29)" in final_output['final_answer'] or "(P28)" in final_output['final_answer']:
        console.print("\n[bold green]🏆 [SUCCESS] 质证员成功定位到 P29 核心证据区，检索漂移已修复！[/bold green]")
    else:
        console.print("\n[bold red]❌ [FAIL] 检索仍未命中核心证据区。[/bold red]")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_witness_intelligence())
