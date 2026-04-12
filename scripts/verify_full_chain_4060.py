
import asyncio
import os
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
import sys

# 路径纠偏
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from spine_cli.core.engine import SpineEngine
from app.core.db import init_db

console = Console()

async def run_full_chain_verification():
    # 1. 初始化
    console.print(Panel("[bold cyan]🛡️ SpineDoc V18.6 全链路压力测试启动[/bold cyan]\n[dim]硬件：RTX 4060 (8GB) | 引擎：GLM-OCR 0.9B[/dim]"))
    
    # 强制初始化 DB 
    await init_db()
    engine = SpineEngine()
    
    test_pdf = "ocr_ceshi/1.pdf"
    if not os.path.exists(test_pdf):
        console.print(f"[red]❌ 找不到测试文件: {test_pdf}[/red]")
        return

    # 2. 执行全量数字化 (Ingest)
    console.print(f"\n[bold yellow]第一阶段：PDF 极速收割 (Ingest)...[/bold yellow]")
    start_time = time.time()
    
    try:
        # 测试前 100 页
        doc_id = await engine.ingest_document(
            test_pdf, 
            limit_pages=100, 
            progress_callback=lambda m: console.print(f"  [blue]>[/blue] {m}")
        )
        ingest_time = time.time() - start_time
        console.print(f"[bold green]✅ Ingest 完成！[/bold green] 耗时: {ingest_time:.2f}s | ID: {doc_id}")
    except Exception as e:
        console.print(f"[bold red]❌ Ingest 失败:[/bold red] {str(e)}")
        import traceback
        console.print(traceback.format_exc())
        return

    # 3. 执行提问
    console.print(f"\n[bold yellow]第二阶段：跨层级语义提问 (RAG Verification)...[/bold yellow]")
    
    queries = [
        "什么是密码学的核心定义？",
        "简述一下 DES 加密算法的基本流程。",
        "公开密钥基础设施 (PKI) 的主要功能是什么？"
    ]

    for i, q in enumerate(queries):
        console.print(f"\n[bold cyan]提问 {i+1}: {q}[/bold cyan]")
        qa_start = time.time()
        
        # 触发级联检索
        results = await engine.hybrid_ask(q, doc_id, limit=5)
        
        if not results:
            console.print("  [red]⚠️ 未找到相关证据。[/red]")
            continue

        console.print(f"  📍 [bold]溯源证据 (物理页码):[/bold]")
        for res in results:
            breadcrumb = res.get('breadcrumb', '未知章节')
            page = res.get('page', '??')
            console.print(f"    - [dim]P{page}[/dim] 章节: [green]{breadcrumb}[/green]")
        
        console.print(f"  ⏱️ 检索耗时: {time.time() - qa_start:.2f}s")

    console.print(Panel("[bold green]🏁 全链路验证圆满完成！[/bold green]"))

if __name__ == "__main__":
    asyncio.run(run_full_chain_verification())
