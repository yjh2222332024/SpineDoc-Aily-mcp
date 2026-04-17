import typer
import asyncio
from pathlib import Path
from typing import Optional, List, Dict, Any
import re
import sys
import os
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.app.services.spine_engine import SpineEngine
from backend.app.services.intelligence.court.color_confidence import (
    COLOR_ICONS,
    COLOR_LABELS,
    ConfidenceColor,
)

app = typer.Typer(
    help="🛡️ SpineDoc (阅脊) - 逻辑刺客级文档审计引擎",
    no_args_is_help=True
)
console = Console()

@app.callback()
def main_callback():
    """
    🛡️ SpineDoc (阅脊) - 逻辑刺客级文档审计引擎

    ═══════════════════════════════════════════════════════════

    🔧 首次使用:
       运行 setup.bat (Windows) 进行一键配置和环境安装

    ═══════════════════════════════════════════════════════════

    📖 常用命令:
      ingest <pdf 文件>              导入 PDF 文档
      ask "<问题>"                   提问 (多文档)
      ask "<问题>" -d <文档 ID>      提问 (单文档)
      ask "<问题>" --online          提问 (联网搜索)
      list                           列出所有文档
      tree <文档 ID>                 查看文档脊梁
      preview <文档 ID>              预览文档切片
      chunks <文档 ID>               查看语义切片

    📜 Git 版本管理:
      git history <ChunkID>          查看 Git 历史
      git show <ChunkID> --to <commit>  查看指定版本
      git revert <ChunkID> --to <commit>  回滚到指定版本
      git diff <ChunkID> -o <old> -n <new>  比较差异

    ═══════════════════════════════════════════════════════════

    💡 提示：输入 spine <command> --help 查看详细用法
    """
    pass

def display_spine_tree(toc: List[Any]):
    """渲染逻辑脊梁树"""
    root_tree = Tree("📁 [bold cyan]逻辑脊梁 (Implicit Spine)[/bold cyan]")

    # 建立层级映射
    nodes = {0: root_tree}
    for item in toc:
        # 🚀 [V1.8.6] 韧性渲染：支持对象或字典
        if hasattr(item, "level"):
            lvl = getattr(item, "level", 1)
            title = getattr(item, "title", "Untitled")
            page = getattr(item, "physical_start", getattr(item, "logical_page", 0))
        else:
            lvl = item.get("level", 1)
            title = item.get("title", "Untitled")
            page = item.get("physical_start", item.get("page", 0))
        
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
                    stop_words_path=stop_words, force_ocr=ocr
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
    api_key: Optional[str] = typer.Option(None, "--key", "-k", help="注入私有 API Key"),
    online: bool = typer.Option(False, "--online", "-o", help="🌐 激活联网证人并触发知识库更新")
):
    """⚖️ 联邦法庭判决：启动多智能体蒙眼辩论与逻辑对线"""
    engine = SpineEngine()
    async def _run():
        console.print(Panel(f"[bold cyan]🎯 查询:[/bold cyan] {query}", border_style="blue"))
        console.print(f"[dim]📡 模式：{'联网联邦法庭 (可能更新知识库)' if online else '本地检索'}[/dim]\n")

        with console.status("[bold green]⚖️ 联邦法庭正在开庭...[/bold green]"):
            results = await engine.hybrid_ask(query, doc_id=doc, limit=limit, api_key=api_key, enable_online=online)

        if not results:
            return

        verdict = results[0]
        console.print("\n")
        console.print(Panel(verdict['text'], title="🏛️ SpineDoc 联邦知识判决书", border_style="cyan", padding=(1, 2)))

        # 显示判决元数据（如果有）
        verdict_meta = verdict.get("verdict_metadata", {})
        if verdict_meta:
            meta_panel = []
            if "confidence" in verdict_meta:
                meta_panel.append(f"[bold]置信度:[/bold] {verdict_meta['confidence']:.2%}")
            if "cited_galaxies" in verdict_meta:
                galaxies = verdict_meta["cited_galaxies"]
                if galaxies:
                    meta_panel.append(f"[bold]引用星系:[/bold] {', '.join(galaxies)}")
            if "knowledge_delta" in verdict_meta:
                delta = verdict_meta["knowledge_delta"]
                if delta.get("has_delta"):
                    meta_panel.append(f"[bold yellow]📈 知识更新:[/bold yellow] {delta.get('updated_chunks', [])} 处变更")
            if meta_panel:
                console.print(Panel("\n".join(meta_panel), border_style="yellow"))

        if len(results) > 1:
            table = Table(title="🔍 逻辑溯源证据链 (Atomic Claims)", box=None, header_style="bold green")
            table.add_column("颜色", style="dim")
            table.add_column("来源", style="dim")
            table.add_column("物理页码", justify="center")
            table.add_column("事实描述", style="white")
            # 显示所有证据（不再限制前 7 条）
            for r in results[1:]:
                # 渲染颜色置信度
                color = r.get('color', 'YELLOW')
                confidence = r.get('confidence', 0.0)
                color_icon = COLOR_ICONS.get(ConfidenceColor(color), '🟡')
                table.add_row(
                    f"{color_icon} {confidence:.2f}",
                    r['breadcrumb'],
                    str(r['page_number']),
                    r['text'][:80] + "..."
                )
            console.print(table)

        # 处理知识更新（如果有）
        if online and verdict_meta.get("knowledge_delta", {}).get("has_delta"):
            from backend.app.services.knowledge.metabolism_manager import get_metabolism_manager
            metabolism = get_metabolism_manager()
            delta = verdict_meta["knowledge_delta"]

            console.print("\n[bold blue]🧬 正在应用知识增量到 Git...[/bold blue]")
            commit_results = await metabolism.apply(delta)

            if commit_results:
                console.print("[green]✅ 知识更新已提交到 Git:[/green]")
                for chunk_id, commit_hash in commit_results.items():
                    console.print(f"  Chunk {chunk_id[:8]} → git:{commit_hash}")
            else:
                console.print("[yellow]⚠️ 无实际变更，跳过 Git 提交[/yellow]")

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
            page = item.get("physical_start", item.get("page", 0))
            spine_tree.add(f"[bold green]{item['title']}[/bold green] [dim](P{page})[/dim]")
        
        console.print("\n")
        console.print(Panel(spine_tree, title="SpineDoc ISR 透视", border_style="cyan"))
        console.print("\n")
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
        table.add_column("创建时间", style="dim")
        table.add_column("更新时间", style="dim")
        for d in docs:
            table.add_row(
                d['id'][:8],
                str(d.get("status", "Unknown")),
                d['filename'],
                str(d['total_pages']),
                d['created_at'][:19],
                d['updated_at'][:19]
            )
        console.print(table)
    asyncio.run(_run())


@app.command()
def preview(
    doc_id: str = typer.Argument(..., help="文档 ID 前缀或完整 ID"),
    limit: int = typer.Option(5, "--limit", "-l", help="显示前 N 个切片")
):
    """📇 预览文档前 N 个语义切片（卡片样式）"""
    engine = SpineEngine()

    import json

    async def _run():
        result = await engine.get_document_preview_chunks(doc_id, limit=limit)

        if "error" in result:
            console.print(f"[red]❌ {result['error']}[/red]")
            return

        console.print("\n")
        console.print(Panel(
            f"[bold cyan]文档:[/bold cyan] {result['filename']}\n"
            f"[bold cyan]预览切片:[/bold cyan] {result['preview_count']} 个",
            title="📇 切片预览",
            border_style="blue",
            padding=(1, 2)
        ))

        for i, chunk in enumerate(result["chunks"], 1):
            json_str = json.dumps(chunk, ensure_ascii=False, indent=2)

            console.print(f"\n[bold cyan]━━━ 切片 #{i} ━━━[/bold cyan]")
            console.print(Panel(
                f"[dim]{json_str}[/dim]",
                title=f"📍 P{chunk['page']} · {chunk['breadcrumb'][:30]}",
                border_style="green",
                padding=(1, 2)
            ))

        console.print(f"\n[dim]💡 提示：使用 'spine chunks {doc_id[:8]}' 查看完整切片列表[/dim]")

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


# 📜 Git 版本控制命令组
git_app = typer.Typer(help="📜 Git 版本管理命令")
app.add_typer(git_app, name="git")


@git_app.command("history")
def git_history(
    chunk_id: str = typer.Argument(..., help="Chunk ID 前缀或完整 ID"),
    limit: int = typer.Option(20, "--limit", "-l", help="显示历史记录数量")
):
    """📜 查看 Chunk 的 Git 版本历史"""
    engine = SpineEngine()

    def _run():
        console.print(Panel(f"[bold cyan]🔍 查询 Chunk:[/bold cyan] {chunk_id[:8]}...", border_style="cyan"))

        try:
            history = engine.get_chunk_history(chunk_id, limit=limit)

            if not history:
                console.print("[yellow]⚠️ 该 Chunk 没有 Git 历史记录[/yellow]")
                return

            table = Table(title="📜 Chunk 版本历史")
            table.add_column("提交哈希", style="cyan")
            table.add_column("时间", style="yellow")
            table.add_column("作者", style="green")
            table.add_column("提交消息", style="white")

            for commit in history:
                table.add_row(
                    commit["short_hash"],
                    commit["timestamp"][:19],
                    commit["author"],
                    commit["message"][:50] + ("..." if len(commit["message"]) > 50 else "")
                )

            console.print("\n")
            console.print(table)
            console.print(f"\n[dim]💡 提示：使用 'spine git show {chunk_id[:8]} --to <commit_hash>' 查看特定版本[/dim]")
            console.print(f"[dim]💡 提示：使用 'spine git revert {chunk_id[:8]} --to <commit_hash>' 回滚[/dim]")

        except Exception as e:
            console.print(f"[red]❌ 查询失败：{e}[/red]")

    _run()


@git_app.command("show")
def git_show(
    chunk_id: str = typer.Argument(..., help="Chunk ID 前缀或完整 ID"),
    to_commit: Optional[str] = typer.Option(None, "--to", "-t", help="查看特定提交版本")
):
    """📄 查看 Chunk 内容（当前版本或历史版本）"""
    engine = SpineEngine()

    def _run():
        if to_commit:
            console.print(Panel(f"[bold cyan]🔍 查询 Chunk:[/bold cyan] {chunk_id[:8]} @ {to_commit[:8]}", border_style="yellow"))
            try:
                data = engine.get_chunk_content(chunk_id, to_commit)
                if data:
                    console.print("\n")
                    console.print(Panel(
                        data["content"],
                        title="📄 Chunk 内容 (历史版本)",
                        border_style="cyan",
                        padding=(1, 2)
                    ))
                    console.print(f"\n[dim]元数据：{data.get('metadata', {})}[/dim]")
                else:
                    console.print("[red]❌ 无法读取该版本的内容[/red]")
            except Exception as e:
                console.print(f"[red]❌ 读取失败：{e}[/red]")
        else:
            console.print(Panel(f"[bold cyan]🔍 查询 Chunk:[/bold cyan] {chunk_id[:8]} (当前版本)", border_style="green"))
            try:
                data = engine.get_chunk_content(chunk_id)
                if not data:
                    console.print("[yellow]⚠️ 该 Chunk 没有 Git 记录[/yellow]")
                    return

                console.print("\n")
                console.print(Panel(
                    data["content"],
                    title="📄 Chunk 内容 (当前版本)",
                    border_style="green",
                    padding=(1, 2)
                ))
                console.print(f"\n[dim]更新时间：{data.get('updated_at', 'Unknown')}[/dim]")
                console.print(f"\n[dim]元数据：{data.get('metadata', {})}[/dim]")
            except Exception as e:
                console.print(f"[red]❌ 读取失败：{e}[/red]")

    _run()


@git_app.command("revert")
def git_revert(
    chunk_id: str = typer.Argument(..., help="Chunk ID 前缀或完整 ID"),
    to_commit: str = typer.Option(..., "--to", "-t", help="回滚到的目标提交哈希"),
    yes: bool = typer.Option(False, "--yes", "-y", help="确认回滚（跳过确认提示）")
):
    """♻️ 回滚 Chunk 到指定 Git 提交版本"""
    engine = SpineEngine()

    def _run():
        console.print(Panel(
            f"[bold yellow]⚠️ 警告：回滚操作[/bold yellow]\n\n"
            f"Chunk: [cyan]{chunk_id[:8]}[/cyan]\n"
            f"回滚到：[green]{to_commit[:8]}[/green]\n\n"
            f"[dim]此操作会创建一个新的 Git 提交，将 Chunk 内容恢复到目标版本。[/dim]",
            border_style="yellow",
            padding=(1, 2)
        ))

        if not yes:
            response = typer.confirm("确认执行回滚？")
            if not response:
                console.print("[yellow]❌ 回滚已取消[/yellow]")
                return

        try:
            success = engine.revert_chunk(chunk_id, to_commit)
            if success:
                console.print(f"\n[green]✅ Chunk {chunk_id[:8]} 已成功回滚到 {to_commit[:8]}[/green]")
                console.print(f"\n[dim]💡 提示：使用 'spine git history {chunk_id[:8]}' 查看更新后的历史[/dim]")
            else:
                console.print(f"[red]❌ 回滚失败[/red]")
        except Exception as e:
            console.print(f"[red]❌ 回滚失败：{e}[/red]")

    _run()


@git_app.command("diff")
def git_diff(
    chunk_id: str = typer.Argument(..., help="Chunk ID 前缀或完整 ID"),
    old: str = typer.Option(..., "--old", "-o", help="旧提交哈希"),
    new: str = typer.Option(..., "--new", "-n", help="新提交哈希")
):
    """🔍 比较 Chunk 在两个 Git 提交之间的差异"""
    engine = SpineEngine()

    def _run():
        console.print(Panel(
            f"[bold cyan]📊 Chunk 差异对比[/bold cyan]\n\n"
            f"Chunk: [cyan]{chunk_id[:8]}[/cyan]\n"
            f"[dim]{old[:8]} → {new[:8]}[/dim]",
            border_style="cyan",
            padding=(1, 2)
        ))

        try:
            diff = engine.diff_chunks(chunk_id, old, new)

            if diff:
                console.print("\n")
                for line in diff.split("\n"):
                    if line.startswith("+") and not line.startswith("+++"):
                        console.print(f"[green]{line}[/green]")
                    elif line.startswith("-") and not line.startswith("---"):
                        console.print(f"[red]{line}[/red]")
                    else:
                        console.print(f"[dim]{line}[/dim]")
            else:
                console.print("[yellow]⚠️ 两个版本之间没有差异[/yellow]")
        except Exception as e:
            console.print(f"[red]❌ 差异对比失败：{e}[/red]")

    _run()


# 🛠️ 配置管理命令
@app.command("setup")
def setup_config():
    """🔧 运行配置向导（交互式配置 API Key 等）"""
    # 动态导入，避免循环依赖
    import subprocess
    setup_script = Path(__file__).parent.parent / "spine_setup.py"
    subprocess.run([sys.executable, str(setup_script)])


@app.command("check")
def check_config():
    """📋 检查配置状态"""
    # 读取 .env 文件并检查配置
    env_file = Path(__file__).parent.parent / ".env"

    config = {}
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    config[key.strip()] = value.strip()

    # 检查配置
    checks = {
        "database": {"name": "数据库配置", "required": True},
        "llm": {"name": "LLM 配置", "required": True},
        "embedding": {"name": "向量模型配置", "required": True},
        "vlm": {"name": "VLM 配置", "required": True},
        "tavily": {"name": "联网搜索 (可选)", "required": False},
    }

    if config.get("DATABASE_URL"):
        checks["database"]["status"] = "configured"
    if config.get("LLM_API_KEY") and config.get("LLM_BASE_URL"):
        checks["llm"]["status"] = "configured"
    if config.get("EMBEDDING_API_KEY") and config.get("EMBEDDING_BASE_URL"):
        checks["embedding"]["status"] = "configured"
    if config.get("VLM_API_KEY") and config.get("VLM_BASE_URL"):
        checks["vlm"]["status"] = "configured"
    if config.get("TAVILY_API_KEY"):
        checks["tavily"]["status"] = "configured"

    # 显示状态
    print("\n📋 配置检查\n")

    required_checks = {k: v for k, v in checks.items() if v.get("required", True)}
    optional_checks = {k: v for k, v in checks.items() if not v.get("required", False)}

    required_configured = sum(1 for c in required_checks.values() if c.get("status") == "configured")
    optional_configured = sum(1 for c in optional_checks.values() if c.get("status") == "configured")

    print(f"必需配置：{required_configured}/{len(required_checks)}")
    print(f"可选配置：{optional_configured}/{len(optional_checks)}\n")

    for info in checks.values():
        status = info.get("status", "missing")
        icon = "✓" if status == "configured" else "⚠"
        required_tag = "[必需]" if info.get("required", True) else "[可选]"
        color = "green" if status == "configured" else "yellow"
        print(f"  {icon} {info['name']} {required_tag}")

    print()


@app.command("models")
def manage_models(
    action: str = typer.Argument("list", help="操作类型：list, download, clean"),
    all_models: bool = typer.Option(False, "--all", "-a", help="下载所有模型（包括可选）"),
    mirror: bool = typer.Option(False, "--mirror", "-m", help="使用国内镜像加速"),
):
    """📦 管理 AI 模型（下载、清理、列表）"""
    import subprocess

    download_script = Path(__file__).parent.parent / "scripts" / "download_models.py"

    if action == "list":
        subprocess.run([sys.executable, str(download_script), "--list"])
    elif action == "download":
        if all_models:
            cmd = [sys.executable, str(download_script), "--all"]
        else:
            cmd = [sys.executable, str(download_script), "--required"]
        if mirror:
            cmd.append("--mirror")
        subprocess.run(cmd)
    elif action == "clean":
        subprocess.run([sys.executable, str(download_script), "--clean"])
    else:
        print(f"未知操作：{action}")
        print("使用 spine models --help 查看帮助")


if __name__ == "__main__":
    app()
