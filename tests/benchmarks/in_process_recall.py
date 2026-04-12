import os
import sys
import asyncio
import time
from rich.console import Console
from rich.table import Table

# 强力路径注入
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
    sys.path.insert(0, os.path.join(project_root, "backend"))

try:
    from spine_cli.core.engine import SpineEngine
except ImportError as e:
    print(f"❌ 核心引擎导入失败: {e}")
    sys.exit(1)

console = Console()

async def run_hydrated_benchmark():
    # 1. 初始化引擎
    engine = SpineEngine()
    docs = engine.list_documents()
    
    if not docs:
        print("❌ 知识库为空！")
        return

    table = Table(title="SpineDoc (v1.2.0) [ISR + Vector] 联调测评报告")
    table.add_column("Query (RAG 核心挑战)", style="cyan", width=45)
    table.add_column("状态", style="bold")
    table.add_column("召回章节 & 物理页码", style="green")
    table.add_column("模式", style="magenta")
    table.add_column("耗时 (ms)", justify="right")

    test_queries = [
        {"q": "GraphRAG 相比传统向量 RAG 的核心优势在哪？"},
        {"q": "如何通过逻辑脊梁重建（ISR）提升长文本召回率？"},
        {"q": "级联检索（Cascading Retrieval）在长文本中的 Token 节省率是多少？"},
        {"q": "ISR 隐含脊梁重建如何解决非结构化 PDF 的目录缺失问题？"}
    ]

    # 获取最新入库的文档进行深度穿透测试
    target_doc = docs[-1]
    console.print(f"🎯 [bold]联调目标: {target_doc['filename']}[/bold]")
    console.print(f"📡 [dim]向量库状态: {'Ready' if target_doc.get('vectorized') else 'Unavailable'}[/dim]\n")

    results = []
    for item in test_queries:
        start_time = time.time()
        try:
            # 🚀 核心：hybrid_ask 会自动执行 ISR 路由 + 向量库精准狙击
            search_results = await engine.hybrid_ask(item["q"], target_doc["id"], limit=3)
            duration = int((time.time() - start_time) * 1000)
            
            is_hit = len(search_results) > 0
            if is_hit:
                best_hit = search_results[0]
                # 识别是向量召回还是逻辑兜底
                mode = "Vector" if best_hit.get("rerank_score") or best_hit.get("_distance") else "ISR-Only"
                info = f"{best_hit.get('breadcrumb', 'N/A')[:15]} (P{best_hit.get('page', '?')})"
            else:
                mode, info = "N/A", "N/A"
            
            table.add_row(
                item["q"][:43] + "...",
                "[bold green]PASS[/bold green]" if is_hit else "[bold red]FAIL[/bold red]",
                info,
                mode,
                str(duration)
            )
            results.append(is_hit)
        except Exception as e:
            print(f"⚠️ 联调错误: {e}")
            continue

    console.print(table)
    hits = sum(1 for r in results if r)
    print(f"\n🎯 [bold yellow]ISR + Vector 综合召回率: {(hits/len(results))*100:.2f}%[/bold yellow]\n")

if __name__ == "__main__":
    asyncio.run(run_hydrated_benchmark())
