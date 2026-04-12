
import asyncio
import os
import time
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.table import Table
import sys

# 路径对齐
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from spine_cli.core.engine import SpineEngine
from app.core.db import get_async_sessionmaker
from app.core.models import Document
from app.core.config import settings
from sqlalchemy import select

console = Console()

async def run_precision_test():
    console.print(Panel("[bold green]🧪 SpineDoc RAG 精度与逻辑溯源终极测试[/bold green]\n[dim]目标：验证 406 页长文档的‘穿透力’与‘逻辑感知’[/dim]"))
    
    engine = SpineEngine()
    
    # 🚀 [V19.11] 修正：从数据库获取最新的文档
    async_session = get_async_sessionmaker()
    async with async_session() as session:
        stmt = select(Document).order_by(Document.created_at.desc()).limit(1)
        res = await session.execute(stmt)
        target_doc = res.scalar_one_or_none()
        
    if not target_doc:
        console.print("[red]❌ 数据库中无文档，请先运行 spine ingest。[/red]")
        return
    
    doc_id = str(target_doc.id)
    console.print(f"🎯 [Target] 锁定测试目标: [bold cyan]{target_doc.filename}[/bold cyan] (ID: {doc_id})")

    # 定义三级难度问题
    test_cases = [
        {
            "level": "L1-细节精度",
            "q": "详细描述书中提到的 DES 算法中 S 盒（S-box）的替换逻辑和作用。",
            "focus": "验证 0.8x 缩放下复杂公式和算法细节的 OCR 还原度。"
        },
        {
            "level": "L2-逻辑演进",
            "q": "根据第二篇‘对称密码’的内容，总结分组密码（如AES/SM4）相比于序列密码（如祖冲之密码）在设计哲学上的核心演进。",
            "focus": "验证系统是否能跨章节（第3章与第4章）进行逻辑聚合。"
        },
        {
            "level": "L3-物理溯源",
            "q": "书中关于‘抗量子计算密码’（第八章）提到的格密码（Lattice-based Crypto）是如何应对量子威胁的？请给出具体的物理页码参考。",
            "focus": "验证 Offset +15 对齐后，P213 之后的深层内容是否能精准定位。"
        }
    ]

    for i, case in enumerate(test_cases):
        console.print(f"\n[bold yellow]测试 {i+1} [{case['level']}]:[/bold yellow] {case['q']}")
        console.print(f"[dim]验证点: {case['focus']}[/dim]")
        
        start_time = time.time()
        
        # 🚀 核心：调用集成后的 hybrid_ask (逻辑感知检索)
        # 这会自动触发：逻辑溯源 -> 动态 OCR 补全 -> 结构化总结
        results = await engine.hybrid_ask(case['q'], doc_id, limit=5)
        
        if not results:
            console.print("  [red]⚠️ 检索失败，未能找到逻辑切片。[/red]")
            continue

        # 打印溯源路径
        path_table = Table(title="🚀 SpineDoc V37.1 逻辑溯源证据链", box=None, header_style="bold blue")
        path_table.add_column("Rank", justify="center")
        path_table.add_column("章节路径 (Breadcrumb)", style="green")
        path_table.add_column("校准页码", justify="center")
        path_table.add_column("Base Score", justify="center")
        path_table.add_column("Boost", justify="center")
        path_table.add_column("Final Score", justify="center", style="bold yellow")
        path_table.add_column("内容片段摘要", style="dim")

        for idx, res in enumerate(results):
            # 提取元数据中的分值
            # 注意：这里的 res 是 cascading_retriever 返回的格式
            b_score = res.get("score", 0) / res.get("_pyramid_boost", 1.0) if res.get("_pyramid_boost", 1.0) > 0 else 0
            
            path_table.add_row(
                str(idx+1),
                res.get('breadcrumb', 'Unknown'),
                f"P{res.get('page_number', '??')}",
                f"{b_score:.3f}",
                f"{res.get('_pyramid_boost', 1.0):.1f}x",
                f"{res.get('score', 0):.3f}",
                res['text'][:40].replace("\n", " ") + "..."
            )
        
        console.print(path_table)

        # 调用 LLM 生成最终答案 (模拟 CLI ask 逻辑)
        context = "\n\n".join([f"章节: {r.get('breadcrumb','')} \n内容: {r['text']}" for r in results])
        sys_prompt = f"你是一个专业的长文档研读引擎(SpineDoc)。请基于提供的切片精准回答，注明章节和页码。参考资料:\n{context}"
        
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        
        console.print(f"\n[bold blue]🧠 Spine AI 逻辑透析:[/bold blue]")
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[{"role": "system", "content": sys_prompt}, {"role": "user", "content": case['q']}],
            temperature=0.1
        )
        console.print(response.choices[0].message.content)
        console.print(f"\n[dim]⏱️ 总耗时: {time.time() - start_time:.2f}s[/dim]")
        console.print("-" * 60)

    console.print(Panel("[bold green]🏁 406 页全链路精度测试完成！[/bold green]"))

if __name__ == "__main__":
    asyncio.run(run_precision_test())
