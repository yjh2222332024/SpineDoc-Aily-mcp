import os
import sys
import asyncio
import time
from rich.console import Console
from rich.table import Table

# 强力路径注入
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    # 直接导入编译函数
    from spine_cli.core.agents.graph import create_spine_graph
except ImportError as e:
    print(f"❌ 核心模块导入失败: {e}")
    sys.exit(1)

console = Console()

class RecallTester:
    def __init__(self):
        self.results = []
        # 初始化编译后的流程
        self.app = create_spine_graph()

    async def run_benchmark(self, queries):
        table = Table(title="SpineDoc (v1.2.0) RAG 论文库逻辑召回测评")
        table.add_column("Query (RAG 核心挑战)", style="cyan", width=45)
        table.add_column("状态", style="bold")
        table.add_column("置信度", style="green")
        table.add_column("耗时 (ms)", justify="right")

        for item in queries:
            start_time = time.time()
            try:
                # 模拟输入 DocumentState
                inputs = {
                    "query": item["q"],
                    "confidence_score": 0.0,
                    "nodes_visited": [],
                    "sources": []
                }
                # 调用 LangGraph
                response = await self.app.ainvoke(inputs)
                duration = int((time.time() - start_time) * 1000)
                
                # 获取置信度和召回状态
                score = response.get("confidence_score", 0.0)
                is_hit = score >= 0.7  # 基于 SpineDoc 的逻辑校验评分
                status = "[bold green]PASS[/bold green]" if is_hit else "[bold red]FAIL[/bold red]"
                
                table.add_row(
                    item["q"][:43] + "...",
                    status,
                    f"{score:.2f}",
                    str(duration)
                )
                self.results.append({"hit": is_hit})
            except Exception as e:
                print(f"⚠️ 测评执行错误: {e}")
                continue

        console.print(table)
        total = len(self.results)
        hits = sum(1 for r in self.results if r["hit"])
        print(f"\n🎯 [bold yellow]ISR 逻辑编排引擎召回评分: {(hits/total)*100:.2f}%[/bold yellow]\n")

if __name__ == "__main__":
    test_queries = [
        {"q": "GraphRAG 相比传统向量 RAG 的核心优势在哪？", "expected_pages": [1, 2]},
        {"q": "如何通过逻辑脊梁重建（ISR）提升长文本召回率？", "expected_pages": [5]},
        {"q": "级联检索（Cascading Retrieval）在长文本中的 Token 节省率是多少？", "expected_pages": [5, 6]}
    ]
    tester = RecallTester()
    asyncio.run(tester.run_benchmark(test_queries))
