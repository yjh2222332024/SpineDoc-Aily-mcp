
import os
import sys
import asyncio
from pathlib import Path
import typer
from rich.console import Console
from rich.panel import Panel
from typing import Optional

# 🏛️ 架构锚定
BACKEND_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_ROOT))

from app.services.spine_engine import SpineEngine
from app.infra.lark_cli_reporter import LarkCliReporter
from app.infra.memory.amem_adapter import AmemAdapter

app = typer.Typer(help="SpineDoc 逻辑审计核心 - OpenClaw 桥接版")
console = Console()

async def _audit_logic(file_path: str, query: str, chat_id: str):
    """内部异步审计逻辑"""
    reporter = LarkCliReporter()
    memory = AmemAdapter()
    engine = SpineEngine(reporter=reporter, memory=memory)
    
    console.print(f"🚀 [Core] 正在审计文件: {file_path}")
    # 1. 导入并提取脊梁
    ingest_res = await engine.ingest_document(file_path)
    doc_id = ingest_res["id"]
    
    # 2. 执行联邦质证
    console.print(f"⚖️ [Core] 正在针对问题执行质证: {query}")
    results = await engine.hybrid_ask(query, doc_id=doc_id, chat_id=chat_id, sync_to_bitable=True)
    
    console.print("✅ [Core] 审计完成，结果已通过飞书卡片送达。")

@app.command()
def audit(
    file_path: str = typer.Option(..., "--file", help="PDF 文件路径"),
    query: str = typer.Option(..., "--query", help="审计问题"),
    chat_id: str = typer.Option(..., "--chat-id", help="飞书会话 ID")
):
    """启动逻辑审计流水线"""
    asyncio.run(_audit_logic(file_path, query, chat_id))

@app.command()
def diff(
    chunk_id: str = typer.Option(..., "--chunk-id", help="逻辑块 ID"),
    chat_id: str = typer.Option(..., "--chat-id", help="飞书会话 ID")
):
    """查看特定逻辑块的历史演变 (Git Diff)"""
    async def _diff_logic():
        engine = SpineEngine(reporter=LarkCliReporter())
        # 获取 Git 历史
        history = engine.get_chunk_history(chunk_id, limit=2)
        if len(history) < 2:
            diff_text = "这是该逻辑点的初始版本，尚无演变记录。"
        else:
            diff_text = engine.diff_chunks(chunk_id, history[1]["hash"], history[0]["hash"])
        
        # 封装成卡片发送
        from spine_interaction.cards.builder import LarkCardBuilder
        builder = LarkCardBuilder()
        verdict_mock = {
            "text": f"🔍 **逻辑演变 Diff (Git)**\n```diff\n{diff_text}\n```",
            "color": "BLUE",
            "verdict_metadata": {"confidence": 1.0, "cited_galaxies": ["Git 司法公证处"]}
        }
        await engine.reporter.report_verdict(verdict_mock, chat_id)

    asyncio.run(_diff_logic())

if __name__ == "__main__":
    app()
