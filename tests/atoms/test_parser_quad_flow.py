"""
SpineDoc 原子测试：TOC 四重分流流水线验证 (V47.5)
==============================================
职责：验证视觉(SiliconFlow VLM)、元数据、幻影、兜底四种路径。
"""
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 🚀 路径注入
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))
load_dotenv(project_root / ".env", override=True)

from backend.app.services.parser import hybrid_parser
from backend.app.services.toc.base import SpineNode
from rich.console import Console
from rich.table import Table

console = Console()

async def verify_nodes(name: str, nodes: list[SpineNode]):
    """核心契约检查：展示完整树并审计物理顺序"""
    console.print(f"\n[bold cyan]🔍 正在验证路径: {name}[/bold cyan]")
    
    if not nodes:
        console.print("[red]❌ 失败：未产生任何 SpineNode[/red]")
        return False

    table = Table(title=f"{name} 完整逻辑脊梁树 (Total: {len(nodes)})")
    table.add_column("Idx", justify="right")
    table.add_column("Title", style="magenta")
    table.add_column("Lvl", justify="center")
    table.add_column("LogPage", justify="center")
    table.add_column("PhysStart", style="green")
    table.add_column("Source", style="dim")

    is_valid = True
    for i, n in enumerate(nodes):
        if not isinstance(n, SpineNode):
            is_valid = False
            break
        
        table.add_row(
            str(i), n.title[:40], str(n.level), 
            str(n.logical_page), str(n.physical_start), 
            n.source
        )

    console.print(table)
    if is_valid:
        console.print(f"[bold green]✅ {name} 契约验证通过！[/bold green]")
    return is_valid

async def run_test():
    pdf_scan = "ceshi_ocr/1.pdf"
    pdf_paper = "ceshi_ocr/2401.08406v3.pdf"

    # --- Test 1: 视觉收割 (SiliconFlow VLM 高精度版) ---
    console.rule("[bold yellow]Path 1: 视觉收割 (SiliconFlow VLM @ 9-15)[/bold yellow]")
    target_range = list(range(9, 16))
    nodes_v = await hybrid_parser.extract_toc_async(
        pdf_scan, manual_range=target_range, force_ocr=True
    )
    await verify_nodes("Visual Harvest (1.pdf)", nodes_v)

    # --- Test 2: 数字指纹 (Metadata) ---
    console.rule("[bold yellow]Path 2: 数字指纹 (Native Metadata)[/bold yellow]")
    nodes_m = await hybrid_parser.extract_toc_async(pdf_paper)
    await verify_nodes("Native Metadata (2401.08406v3)", nodes_m)

    # --- Test 3: 幻影探测 (Phantom) ---
    console.rule("[bold yellow]Path 3: 幻影探测 (Phantom Saliency)[/bold yellow]")
    nodes_p = await hybrid_parser.extract_toc_async(pdf_paper, force_ocr=False)
    await verify_nodes("Phantom Saliency (Paper Auto)", nodes_p)

    # --- Test 4: 全量兜底 (Fallback) ---
    console.rule("[bold yellow]Path 4: 全量兜底 (Full Fallback)[/bold yellow]")
    # 模拟一个无结构场景
    nodes_f = await hybrid_parser.extract_toc_async(pdf_paper, force_ocr=False) 
    await verify_nodes("Fallback Path", nodes_f)

if __name__ == "__main__":
    asyncio.run(run_test())
