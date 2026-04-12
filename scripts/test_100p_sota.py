
import asyncio
import sys
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel

# 路径对齐
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from spine_cli.core.engine import SpineEngine
from scripts.force_reset_doc import force_reset

console = Console()

async def run_sota_100p_test():
    console.print(Panel("[bold cyan]🏆 SpineDoc V29.1 SOTA 精度实测 (100页采样版)[/bold cyan]"))
    
    engine = SpineEngine()
    file_path = "ocr_ceshi/1.pdf"
    
    # 1. 强制重置
    await force_reset()
    
    # 2. 启动 V29.0 上下文增强版 Ingest
    console.print(f"🚀 [Ingest] 正在启动 4060 动力收割，目标：[bold]前 100 页[/bold]...")
    console.print(f"[dim]核心逻辑：Contextual Retrieval + 章节摘要注入[/dim]")
    
    start_ingest = time.time()
    doc_id = await engine.ingest_document(
        file_path, 
        manual_toc_range=list(range(9, 15)), 
        limit_pages=100,
        progress_callback=lambda m: console.print(f"  > [dim]{m}[/dim]")
    )
    console.print(f"✅ [Ingest Done] 耗时: {time.time() - start_ingest:.2f}s\n")

    # 3. 运行 SOTA 级“灵魂拷问”
    # 这个问题的核心是测试系统是否能从“算法实现”中区分出“标准化进展”
    query = "详细说明中国商用密码算法 SM4 在国际标准化方面（如被 ISO/IEC 采纳）的具体背景和意义。"
    
    console.print(Panel(f"🔍 [Query] {query}", border_style="yellow"))
    
    start_ask = time.time()
    # 触发 V28.1 + V29.0 级联检索
    results = await engine.hybrid_ask(query, doc_id, limit=30)
    
    console.print(f"\n⏱️ [RAG Done] 耗时: {time.time() - start_ask:.2f}s\n")

    if not results:
        console.print("[red]❌ 未能定位证据。[/red]")
        return

    # 4. 结果展示 (证据预览)
    import re
    from rich.table import Table
    from rich.text import Text

    console.print("[bold green]📍 最终捕获的逻辑证据链:[/bold green]")
    for i, res in enumerate(results):
        raw_text = res.get('content', '')
        # 尝试提取我们注入的摘要
        summary_match = re.search(r"【本段上下文路径: (.*?)】", raw_text)
        summary = summary_match.group(1) if summary_match else "N/A"
        
        preview = raw_text.split("】")[-1].strip()[:150].replace("\n", " ") + "..."
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row(f"[bold magenta][{i+1}] 页码:[/bold magenta]", f"P{res.get('page_number')}")
        table.add_row(f"[bold green]    路径:[/bold green]", res.get('breadcrumb', 'Unknown'))
        table.add_row(f"[bold cyan]    上下文精要:[/bold cyan]", Text(summary, style="italic yellow"))
        
        console.print(Panel(preview, title=f"证据 #{i+1}", border_style="blue"))
        console.print(table)
        console.print("-" * 40)

if __name__ == "__main__":
    asyncio.run(run_sota_100p_test())
