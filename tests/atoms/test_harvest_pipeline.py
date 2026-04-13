import asyncio
import sys
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# 🚀 路径锚定
project_root = Path(__file__).resolve().parent.parent.parent
load_dotenv(project_root / ".env", override=True)

# 🏛️ 强制 CPU 模式，彻底杜绝 DLL 冲突
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
sys.path.append(str(project_root))

from backend.app.services.toc.manager import toc_manager
from backend.app.services.toc.base import SpineNode
from backend.app.services.rag.spine_splitter import SpineSplitter
from rich.console import Console
from rich.table import Table

console = Console()

async def run_integration_test():
    console.rule("[bold yellow]SpineDoc 集成原子测试：CPU 纯净分片验证[/bold yellow]")

    # 1. 加载测试数据 (内置 Qwen3 识别出的 9-15 页真实样本片段)
    toc_data_raw = [
        {"title": "第一篇 基础知识", "logical_page": 3, "level": 1},
        {"title": "第1章 信息安全概论", "logical_page": 3, "level": 2},
        {"title": "1.1 信息安全是信息时代永恒的需求", "logical_page": 3, "level": 3},
        {"title": "1.2 信息安全的一些基本原则", "logical_page": 3, "level": 3}
    ]

    # 2. 脊梁重构 (Offset=15)
    nodes = [SpineNode(**it) for it in toc_data_raw]
    processed_nodes = toc_manager.process_raw_toc(nodes, total_pages=500)
    
    # 3. 提取叶子节点
    leaves = toc_manager.get_leaf_nodes(processed_nodes)
    console.print(f"✅ 成功提取 [bold green]{len(leaves)}[/bold green] 个叶子节点。")

    # 4. 模拟分片测试 (包含明确的语义转折)
    target_leaf = leaves[0] 
    mock_text = """信息安全是信息时代永恒的需求。随着互联网的普及，数据安全变得日益重要。
    这里是一个显著的语义转折点。我们现在要讨论的是网络攻防演练中的逻辑隔离。
    这一句和上一句意思完全不同。这一段专注于物理硬件的防护措施。
    这是本章节的最后一段话，绝对不能超出其物理边界。"""

    console.print(f"\n🧩 [Action] 正在对叶子节点 [bold cyan]'{target_leaf.title}'[/bold cyan] 进行语义分片...")
    console.print("⏳ (正在利用 BGE-Small CPU 模型执行向量化计算...)")
    
    # 启动分片器
    splitter = SpineSplitter(threshold=0.82)
    chunks = await splitter.split_chapter_stream(
        text=mock_text, 
        toc_item_id=str(target_leaf.id), 
        breadcrumb=target_leaf.title
    )

    # 5. 验证分片结果
    chunk_table = Table(title=f"产出的元分片 (Total: {len(chunks)})")
    chunk_table.add_column("Idx", justify="right")
    chunk_table.add_column("Content Preview", style="white")
    chunk_table.add_column("Len", justify="right")
    
    for i, c in enumerate(chunks):
        chunk_table.add_row(str(i), c["content"][:60] + "...", str(len(c["content"])))
    
    console.print(chunk_table)
    
    # 物理溯源审计
    is_traceable = all(c["toc_item_id"] == str(target_leaf.id) for c in chunks)
    
    if is_traceable and len(chunks) > 1:
        console.print("\n[bold green]✨ 集成测试通过！成功实现 CPU 隔离下的高灵敏度语义分片。[/bold green]")
    else:
        console.print("\n[red]❌ 测试未达标：分片数量不足或溯源失败。[/red]")

if __name__ == "__main__":
    asyncio.run(run_integration_test())
