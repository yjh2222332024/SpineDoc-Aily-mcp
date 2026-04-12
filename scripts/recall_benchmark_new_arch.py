
import asyncio
import os
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
import sys

# 路径纠偏
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from spine_cli.core.engine import SpineEngine
from app.core.db import init_db

console = Console()

async def run_toc_debug():
    console.print(Panel("[bold magenta]🔍 SpineDoc 目录精准调试模式 (HITL 9-15页)[/bold magenta]"))
    
    # 🚀 1. 自动删除旧缓存，保证推倒重来
    test_pdf = "ocr_ceshi/1.pdf"
    cache_file = f"{test_pdf}.ocr_cache.json"
    if os.path.exists(cache_file):
        os.remove(cache_file)
        console.print(f"[yellow]🧹 已清理旧缓存文件: {cache_file}[/yellow]")

    await init_db()
    engine = SpineEngine()

    # 🚀 2. 仅收割目录区间 (HITL 模式)
    console.print(f"\n[bold yellow]Step 1: 正在对第 9-15 页进行机械式目录提取...[/bold yellow]")
    start_ingest = time.time()
    
    try:
        # 我们这里利用 limit_pages=15 限制全书处理，仅让 ISR 跑完目录区间
        doc_id = await engine.ingest_document(
            test_pdf, 
            manual_toc_range=[9, 10, 11, 12, 13, 14, 15],
            limit_pages=15, # 🛑 调试模式：处理完目录后立刻停止
            progress_callback=lambda m: console.print(f"  [blue]>[/blue] {m}")
        )
        ingest_duration = time.time() - start_ingest
        console.print(f"✨ [目录提取完成] 耗时: {ingest_duration:.2f}s | ID: {doc_id}")

        # 🚀 3. 打印 TOC 逻辑树供核对
        console.print(f"\n[bold yellow]Step 2: 逻辑脊梁核对树 (ISR Reconstruction Tree)[/bold yellow]")
        doc_data = await engine.get_document(doc_id)
        
        if doc_data and doc_data.get("toc"):
            spine_tree = Tree(f"[bold blue]📄 {doc_data.get('filename', '1.pdf')} (自动对齐：Offset +{doc_data.get('page_offset', 0)})[/bold blue]")
            
            # 获取引擎计算的偏移量
            offset = doc_data.get("page_offset", 0)
            
            # 按理论页码排序
            sorted_toc = sorted(doc_data["toc"], key=lambda x: x["page"])
            
            for item in sorted_toc:
                theory_page = item['page']
                # 🚀 按照用户要求的逻辑显示：物理页 = 理论页 + 目录接续产生的 Offset
                actual_phys = theory_page + offset
                
                indent = "  " * (item['level'] - 1)
                spine_tree.add(f"{indent}[bold green]{item['title']}[/bold green] [dim]理论: {theory_page}[/dim] [magenta](物理: P{actual_phys})[/magenta]")
            
            console.print(Panel(spine_tree, title="✅ ISR 逻辑脊梁 (物理页码已校准)", border_style="green"))
            
            console.print("\n[bold cyan]💡 调试提示：[/bold cyan]")
            console.print("1. 如果标题有误，可能是 GLM-OCR 的 Markdown 提取正则需要优化。")
            console.print("2. 如果页码错位，请检查 LogicAligner 的 Offset 自动对齐逻辑。")
            
        else:
            console.print("[red]❌ 报错：未能在数据库中找到 TOC 记录！[/red]")

    except Exception as e:
        console.print(f"[bold red]❌ 调试崩溃:[/bold red] {str(e)}")
        import traceback
        console.print(traceback.format_exc())

    console.print(f"\n[bold white]调试结束。如目录准确，请告诉我可以开启 406 页全量正文收割。[/bold white]")

if __name__ == "__main__":
    asyncio.run(run_toc_debug())
