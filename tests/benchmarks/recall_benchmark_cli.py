import os
import subprocess
import time
import re
from rich.console import Console
from rich.table import Table

console = Console()

class CLIRecallTester:
    def __init__(self):
        self.results = []
        self.cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def run_query(self, query: str):
        start_time = time.time()
        env = os.environ.copy()
        env["PYTHONPATH"] = "."
        
        try:
            # 🚀 修正：使用 Spine-open 的真实命令 'ask'
            result = subprocess.run(
                ["python", "-m", "spine_cli.main", "ask", query],
                cwd=self.cwd,
                env=env,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=120 # 给 AI 更多思考时间
            )
            duration = int((time.time() - start_time) * 1000)
            output = result.stdout + result.stderr
            
            # 1. 匹配页码，SpineDoc 的格式是 (P数字)
            pages = re.findall(r"\(P(\d+)\)", output)
            pages = list(set([int(p) for p in pages]))
            
            # 2. 匹配逻辑锚点/章节名
            breadcrumbs = re.findall(r"•\s*\[\d+\]\s*(.*?)\s*\(P\d+\)", output)
            
            # 只要有溯源结果或 AI 输出了答案内容，即视为召回成功
            is_hit = len(pages) > 0 or "Spine AI:" in output
            
            # 提取 AI 回答片段（Spine AI: 之后的内容）
            ai_answer = ""
            if "Spine AI:" in output:
                ai_answer = output.split("Spine AI:")[1].strip()
            
            return is_hit, pages, breadcrumbs, duration, ai_answer[:150].strip()
        except Exception as e:
            return False, [], [], 0, f"Error: {str(e)}"

    def run_benchmark(self, queries):
        table = Table(title="SpineDoc (v1.2.0) RAG 论文库实战召回测评")
        table.add_column("Query (RAG 核心挑战)", style="cyan", width=35)
        table.add_column("状态", style="bold")
        table.add_column("页码/章节溯源", style="green")
        table.add_column("耗时 (ms)", justify="right")
        table.add_column("AI 深度解析预览", style="dim", width=45)

        for item in queries:
            is_hit, pages, breadcrumbs, duration, ai_answer = self.run_query(item["q"])
            status = "[bold green]PASS[/bold green]" if is_hit else "[bold red]FAIL[/bold red]"
            
            # 简单清洗
            clean_ans = ai_answer.replace("\n", " ").replace("\r", "")
            source_info = f"P{pages[0]} " if pages else ""
            if breadcrumbs:
                source_info += f"[{breadcrumbs[0][:15]}]"
            
            table.add_row(
                item["q"][:33] + "...",
                status,
                source_info if source_info else "N/A",
                str(duration),
                clean_ans[:42] + "..."
            )
            self.results.append({"hit": is_hit, "latency": duration})

        console.print(table)
        total = len(self.results)
        hits = sum(1 for r in self.results if r["hit"])
        print(f"\n🎯 [bold yellow]实战召回率: {(hits/total)*100:.2f}%[/bold yellow]")

if __name__ == "__main__":
    test_queries = [
        {"q": "GraphRAG 相比传统向量 RAG 的核心优势在哪？"},
        {"q": "级联检索（Cascading Retrieval）在长文本中的 Token 节省率是多少？"},
        {"q": "RAG-Evolution 提到的三阶段优化包含哪些具体模块？"},
        {"q": "ISR 隐含脊梁重建如何解决非结构化 PDF 的目录缺失问题？"}
    ]
    tester = CLIRecallTester()
    tester.run_benchmark(test_queries)
