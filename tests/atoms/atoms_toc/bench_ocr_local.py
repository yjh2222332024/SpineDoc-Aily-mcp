import asyncio
import time
import torch
import cv2
import fitz
import numpy as np
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table

# 🏛️ 顶级架构锚定
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
import sys
sys.path.append(str(PROJECT_ROOT))

from backend.app.services.ocr.paddle_worker import PaddleWorker
from backend.app.services.ocr.got_worker import GOTWorker

console = Console()

async def benchmark_ocr():
    console.print("[bold cyan]🚀 [OCR-Bench] 启动纯本地 GPU OCR 性能审计...[/bold cyan]")
    
    # 1. 硬件探测
    device = "cuda" if torch.cuda.is_available() else "cpu"
    console.print(f"🎮 Target Device: [bold green]{device.upper()}[/bold green]")
    if device == "cuda":
        console.print(f"🔥 GPU: {torch.cuda.get_device_name(0)}")

    # 2. 预加载 Worker (显式加载到 GPU)
    console.print("⌛ 正在加载模型到显存 (Paddle + GOT)...")
    paddle = PaddleWorker()
    got = GOTWorker()
    
    pdf_path = PROJECT_ROOT / "ceshi_ocr" / "1.pdf"
    if not pdf_path.exists():
        console.print(f"[red]❌ 目标 PDF 不存在: {pdf_path}[/red]")
        return
        
    doc = fitz.open(pdf_path)
    
    table = Table(title="Local OCR GPU Benchmark (Top 10 Pages)")
    table.add_column("Page", justify="center")
    table.add_column("Scout (Paddle)", style="yellow")
    table.add_column("Specialist (GOT)", style="magenta")
    table.add_column("Total", style="bold green")
    table.add_column("Formulas Found", justify="center")

    # 3. 循环压测
    for i in range(10):
        page = doc[i]
        # 使用 2.0 倍率渲染，平衡精度与速度
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0)) 
        img = cv2.imdecode(np.frombuffer(pix.tobytes(), np.uint8), cv2.IMREAD_COLOR)
        
        # A. 侦察阶段 (Paddle)
        t0 = time.time()
        blocks = await paddle.ocr_with_layout(img)
        t_scout = time.time() - t0
        
        # B. 精修阶段 (GOT)
        # 模拟真实逻辑：如果页面包含潜在公式，则触发一次 GOT 精修
        t1 = time.time()
        formulas = [b for b in blocks if b["type"] == "formula"]
        if formulas:
            # 传入整图进行 GOT 精修识别
            _ = await got.recognize(img) 
        t_spec = time.time() - t1
        
        total = t_scout + t_spec
        table.add_row(
            f"P{i+1}",
            f"{t_scout*1000:.0f}ms",
            f"{t_spec*1000:.0f}ms",
            f"{total*1000:.0f}ms",
            str(len(formulas))
        )

    console.print(table)
    console.print(f"\n[bold green]✅ 审计完成。如果 Total < 1500ms，说明 4060 已完美接管算力。[/bold green]")

if __name__ == "__main__":
    asyncio.run(benchmark_ocr())
