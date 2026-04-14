import asyncio
import sys
from pathlib import Path
from uuid import UUID
from rich.console import Console
from rich.tree import Tree

# 🏛️ 顶级架构锚定
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem
from sqlalchemy import select

console = Console()

async def probe_tree():
    console.print("[bold cyan]🌲 [Forensic] 正在重构逻辑脊梁树状全景图...[/bold cyan]")
    session_maker = get_async_sessionmaker()
    
    async with session_maker() as session:
        # 1. 锁定最新文档
        stmt_doc = select(Document).where(Document.filename == '1.pdf').order_by(Document.created_at.desc()).limit(1)
        doc = (await session.execute(stmt_doc)).scalar_one_or_none()
        
        if not doc:
            console.print("[red]❌ 未找到文档记录。[/red]")
            return

        # 2. 获取所有 TOC 项，按照物理顺序和层级排序
        # 🚀 [V48.9] 关键：我们不能只靠 physical_start，还要看原始提取顺序（如果数据库存了的话）
        # 这里我们假设物理顺序基本代表了树的展开顺序
        stmt_toc = select(TocItem).where(TocItem.document_id == doc.id).order_by(TocItem.physical_start, TocItem.level)
        tocs = (await session.execute(stmt_toc)).scalars().all()

        if not tocs:
            console.print("[yellow]⚠️ 无目录数据。[/yellow]")
            return

        # 3. 构造树形结构
        # 使用字典缓存已生成的 Tree 节点，支持 parent_id 查找
        tree_nodes = {}
        root_tree = Tree(f"[bold white]ISR Root: {doc.filename}[/bold white] (Offset: {doc.page_offset})")

        # 为了应对 parent_id 丢失的情况，我们准备一个栈式回退机制
        stack = [(0, root_tree)]

        for t in tocs:
            label = (
                f"[bold cyan]L{t.level}[/bold cyan] [white]{t.title[:50]}[/white] "
                f"[dim]| LogP:{t.page} |[/dim] [bold magenta]Phys:P{t.physical_start}-P{t.physical_end}[/bold magenta]"
            )
            
            # 策略 A：优先尝试根据数据库的 parent_id 挂载
            if t.parent_id and t.parent_id in tree_nodes:
                tree_nodes[t.id] = tree_nodes[t.parent_id].add(label)
            else:
                # 策略 B：栈式层级推断（用于可视化数据库中的扁平存储）
                while stack and stack[-1][0] >= t.level:
                    stack.pop()
                
                parent_tree = stack[-1][1]
                new_branch = parent_tree.add(label)
                tree_nodes[t.id] = new_branch
                stack.append((t.level, new_branch))

        console.print(root_tree)
        console.print(f"\n[dim]Total Nodes: {len(tocs)} | Deepest Level: {max(t.level for t in tocs)}[/dim]")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(probe_tree())
