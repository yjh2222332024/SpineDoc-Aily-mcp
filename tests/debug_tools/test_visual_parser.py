
import sys
import os
from pathlib import Path

# 路径注入
current_dir = Path(__file__).parent.parent.parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / "backend"))

from backend.app.services.parser import HybridParser
from rich.console import Console
from rich.table import Table

console = Console()

def test_visual_rebuild():
    file_path = "ocr_ceshi/1.pdf"
    if not os.path.exists(file_path):
        console.print(f"[red]Error: {file_path} not found.[/red]")
        return

    parser = HybridParser()
    console.print(f"🚀 [bold]Starting Visual ISR Test on:[/bold] {file_path}")
    
    try:
        # 触发视觉解析
        toc = parser.extract_toc(file_path)
        
        if not toc:
            console.print("[yellow]Warning: No TOC items extracted.[/yellow]")
            return

        table = Table(title=f"Extracted Visual Spine (Total: {len(toc)})")
        table.add_column("Level", justify="center")
        table.add_column("Title", style="cyan")
        table.add_column("Page (Logic)", justify="right", style="green")
        
        for item in toc[:20]:  # 只展示前20个
            table.add_row(
                str(item.get("level", "-")),
                item.get("title", "UNTITLED"),
                str(item.get("page", "-"))
            )
        
        console.print(table)
        if len(toc) > 20:
            console.print(f"... and {len(toc)-20} more items.")

    except Exception as e:
        console.print(f"[red]Critical Failure:[/red] {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_visual_rebuild()
