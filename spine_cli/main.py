import typer
import asyncio
from pathlib import Path
from typing import Optional, List, Dict
import re
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from spine_cli.core.engine import SpineEngine

app = typer.Typer(help="🛡️ SpineDoc (阅脊) - 逻辑刺客级文档审计引擎", no_args_is_help=True)
console = Console()

@app.callback()
def main_callback():
    """SpineDoc 审计引擎，输入 --help 查看详情。"""
    pass

def display_spine_tree(toc: List[Dict]):
    """渲染逻辑脊梁树"""
    root_tree = Tree("📁 [bold cyan]逻辑脊梁 (Implicit Spine)[/bold cyan]")

    # 建立层级映射
    nodes = {0: root_tree}
    for item in toc:
        lvl = item.get("level", 1)
        title = item.get("title", "Untitled")
        page = item.get("page", 0)
        
        parent = nodes.get(lvl - 1, root_tree)
        node = parent.add(f"[green]{title}[/green] [dim](P{page})[/dim]")
        nodes[lvl] = node
        
    console.print("\n")
    console.print(root_tree)
    console.print("\n")

@app.command()
def ingest(
    path: str = typer.Argument(..., help="PDF 文件或目录路径"),
    force: bool = typer.Option(False, "--force", "-f", help="强制重新入库"),
    limit: Optional[int] = typer.Option(None, "--limit", "-l", help="限制处理页数"),
    toc_range: Optional[str] = typer.Option(None, "--toc-range", "-t", help="手动指定目录范围，例如 '9,15'"),
    stop_words: Optional[str] = typer.Option(None, "--stop-words", "-s", help="自定义停用词/领域词库文件路径"),
    key: Optional[str] = typer.Option(None, "--key", "-k", help="注入私有 API Key（用于 SLM 调用）"),
    ocr: bool = typer.Option(False, "--ocr", "-o", help="强制使用 OCR 模式（默认自动检测，数字 PDF 优先 Metadata）"),
    font_feature: bool = typer.Option(False, "--font-feature", "-F", help="使用字体特征提取（最快，适合格式化 PDF 如 arXiv 论文）"),
    dev: bool = typer.Option(False, "--dev", help="🚀 开发者模式：强制删除 Checkpoint，从零开始完整重跑")
):
    """🚀 极速流式收割：提取逻辑脊梁并执行语义反哺"""
    engine = SpineEngine()
    p = Path(path)
    
    # ... (原有 toc_range 解析逻辑)
    manual_range = None
    if toc_range:
        try:
            nums = [int(n) for n in re.findall(r'\d+', str(toc_range))]
            if len(nums) == 2:
                start, end = sorted(nums)
                manual_range = [i for i in range(start, end + 1)]
                console.print(f"🎯 [CLI] 已识别目录范围: P{start} -> P{end}")
            else:
                manual_range = nums
        except Exception as e:
            console.print(f"[red]❌ 目录范围解析失败: {e}[/red]")
            return

    async def _run():
        if p.is_file():
            files = [p]
        else:
            files = [f for f in p.glob("*.pdf")]

        console.print(f"[bold blue]📡 发现 {len(files)} 份文档，启动收割程序...[/bold blue]")

        for f in files:
            console.print(f"\n📂 [Processing] {f.name}")

            # 🚀 [V44.2] 任务看门狗：监控死锁
            async def watchdog():
                await asyncio.sleep(180) # 180秒无响应则 dump
                print("\n🚨 [Deadlock-Watchdog] 监测到 ingest 任务超时，正在 dump 任务栈...")
                for task in asyncio.all_tasks():
                    print(f"DEBUG: Task {task.get_name() or 'Unnamed'} -> {task.get_coro()}")
                    # 打印栈
                    stack = task.get_stack()
                    if stack:
                        import traceback
                        traceback.print_stack(stack[-1])

            watchdog_task = asyncio.create_task(watchdog(), name="Deadlock-Watchdog")

            with console.status(f"[bold yellow]正在解析逻辑脊梁...[/bold yellow]"):
                # 🚀 接收结构化结果
                result = await engine.ingest_document(
                    str(f), force=force, limit_pages=limit, manual_toc_range=manual_range,
                    stop_words_path=stop_words, request_api_key=key, force_ocr=ocr,
                    use_font_feature=font_feature, dev_mode=dev
                )

            watchdog_task.cancel() # 解析成功，关闭看门狗

            # 判断结果类型并渲染树
            if isinstance(result, dict):
                doc_id = result["id"]
                display_spine_tree(result.get("toc", []))
            else:
                doc_id = str(result)

            console.print(f"✅ [Success] 文档已入库，ID: {doc_id[:8]}")

            
    asyncio.run(_run())

@app.command()
def ask(
    query: str = typer.Argument(..., help="你的问题"),
    doc: str = typer.Option("all", "--doc", "-d", help="目标文档 ID"),
    limit: int = typer.Option(15, "--limit", "-l", help="召回上限"),
    api_key: Optional[str] = typer.Option(None, "--key", "-k", help="注入私有 API Key")
):
    """⚖️ 联邦法庭判决：启动多智能体蒙眼辩论与逻辑对线"""
    engine = SpineEngine()
    async def _run():
        console.print(Panel(f"[bold cyan]🎯 查询:[/bold cyan] {query}", border_style="blue"))
        with console.status("[bold green]⚖️ 联邦法庭正在开庭...[/bold green]"):
            results = await engine.hybrid_ask(query, doc_id=doc, limit=limit, api_key=api_key)
            
        if not results: return
        verdict = results[0]
        console.print("\n")
        console.print(Panel(verdict['text'], title="🏛️ SpineDoc 联邦知识判决书", border_style="cyan", padding=(1, 2)))
        
        if len(results) > 1:
            table = Table(title="🔍 逻辑溯源证据链 (Atomic Claims)", box=None, header_style="bold green")
            table.add_column("来源", style="dim")
            table.add_column("页码", justify="center")
            table.add_column("事实描述", style="white")
            for r in results[1:8]:
                table.add_row(r['breadcrumb'], str(r['page_number']), r['text'][:80] + "...")
            console.print(table)
    asyncio.run(_run())

@app.command()
def tree(doc_id: str = typer.Argument(..., help="文档 ID 前缀或完整 ID")):
    """🌳 逻辑脊梁透视：可视化展示 ISR 提取出的文档骨架"""
    engine = SpineEngine()
    async def _run():
        doc = await engine.get_document(doc_id)
        if not doc:
            console.print("[red]❌ 未找到文档[/red]")
            return
        
        spine_tree = Tree(f"📄 [bold blue]{doc['filename']}[/bold blue] (Offset: {doc['page_offset']})")
        for item in doc.get("toc", []):
            spine_tree.add(f"[bold green]{item['title']}[/bold green] [dim](P{item['page']})[/dim]")
        
        console.print("\n")
        console.print(Panel(spine_tree, title="SpineDoc ISR 透视", border_style="cyan"))
        console.print("\n")
    asyncio.run(_run())

@app.command()
def nuke():
    """☢️ 一键炸库：清空所有文档、切片与向量索引 (慎用!)"""
    confirm = typer.confirm("⚠️ 确定要彻底清空数据库与物理存储吗？此操作不可逆！")
    if not confirm:
        console.print("[yellow]操作已取消。[/yellow]")
        return
    
    engine = SpineEngine()
    async def _run():
        with console.status("[bold red]正在执行核打击...[/bold red]"):
            await engine.nuke_database()
        console.print("✅ [bold green]清理完成。星系已回归尘埃。[/bold green]")
    asyncio.run(_run())

@app.command()
def list():
    """📂 列出所有已入库的文档"""
    engine = SpineEngine()
    async def _run():
        docs = await engine.list_documents()
        table = Table(title="🏛️ SpineDoc 知识星系")
        table.add_column("ID (前缀)", style="cyan")
        table.add_column("状态", style="yellow")
        table.add_column("文件名", style="green")
        table.add_column("总页数", justify="right")
        for d in docs:
            table.add_row(d['id'][:8], str(d.get("status", "Unknown")), d['filename'], str(d['total_pages']))
        console.print(table)
    asyncio.run(_run())

@app.command("chunks")
def show_chunks(
    doc_id: str = typer.Argument(..., help="文档 ID 前缀或完整 ID"),
    limit: int = typer.Option(20, "--limit", "-l", help="显示 Chunk 数量"),
    page: Optional[int] = typer.Option(None, "--page", "-p", help="筛选特定页码"),
    keyword: Optional[str] = typer.Option(None, "--keyword", "-k", help="筛选包含特定关键词的 Chunk（多个关键词用逗号分隔）")
):
    """🔍 查看文档的语义切片及关键词（jieba 分词结果）"""
    engine = SpineEngine()
    
    async def _run():
        # 1. 获取文档信息
        doc_info = await engine.get_document(doc_id)
        if not doc_info:
            console.print("[red]❌ 未找到文档[/red]")
            return
        
        # 2. 获取语义切片
        chunks = await engine.get_document_chunks(doc_id, limit=limit)
        
        if not chunks:
            console.print("[yellow]⚠️ 该文档没有语义切片[/yellow]")
            return
        
        # 3. 显示文档信息
        console.print("\n")
        console.print(Panel(
            f"[bold cyan]文档:[/bold cyan] {doc_info.get('filename', 'Unknown')}\n"
            f"[bold cyan]总页数:[/bold cyan] {doc_info.get('total_pages', 'Unknown')}\n"
            f"[bold cyan]显示切片数:[/bold cyan] {len(chunks)} 个 (上限：{limit})",
            title="📦 语义切片浏览器",
            border_style="green",
            padding=(1, 2)
        ))
        
        # 解析关键词列表（支持多个关键词，逗号分隔）
        filter_keywords = []
        if keyword:
            filter_keywords = [kw.strip() for kw in keyword.split(',')]
            console.print(f"[dim]🔍 关键词过滤：{filter_keywords}[/dim]\n")
        
        # 4. 显示每个 Chunk 的关键词
        filtered_count = 0
        for i, chunk in enumerate(chunks, 1):
            # 页码筛选
            if page and chunk['page_number'] != page:
                continue
            
            # 关键词筛选
            if filter_keywords:
                chunk_keywords = chunk.get('keywords', [])
                # 检查 Chunk 是否包含任何一个过滤关键词
                if not any(kw in chunk_keywords for kw in filter_keywords):
                    continue
                filtered_count += 1
            
            console.print(f"\n[bold cyan]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold cyan]")
            console.print(f"[bold green]📌 Chunk #{i}[/bold green] | [dim]页码：P{chunk['page_number']}[/dim]")
            console.print(f"[bold blue]🏷️ 关键词:[/bold blue] {', '.join(chunk['keywords']) if chunk['keywords'] else '[无]'}")
            
            if chunk.get('logic_tags'):
                console.print(f"[bold purple]🔗 逻辑标签:[/bold purple] {', '.join(chunk['logic_tags'])}")
            
            console.print(f"[dim]📍 路径：{chunk['breadcrumb']}[/dim]")
            console.print(f"\n[dim]📄 内容预览:[/dim]")
            console.print(f"    {chunk['content']}")
        
        # 5. 显示关键词统计
        all_keywords = []
        for chunk in chunks:
            all_keywords.extend(chunk.get('keywords', []))
        
        if all_keywords:
            from collections import Counter
            keyword_freq = Counter(all_keywords)
            top_keywords = keyword_freq.most_common(15)
            
            console.print("\n")
            console.print(Panel(
                "\n".join([f"{kw}: {count} 次" for kw, count in top_keywords]),
                title="📊 Top 15 高频关键词",
                border_style="yellow",
                padding=(1, 2)
            ))
        
        if filter_keywords:
            console.print(f"\n[dim]💡 提示：共显示 {filtered_count} 个匹配 Chunk（总数：{len(chunks)}）| 使用 --limit 调整显示数量，使用 --page 筛选特定页码[/dim]")
        else:
            console.print(f"\n[dim]💡 提示：使用 --limit 调整显示数量，使用 --page 筛选特定页码，使用 --keyword 筛选关键词[/dim]")
        
    asyncio.run(_run())

if __name__ == "__main__":
    app()
