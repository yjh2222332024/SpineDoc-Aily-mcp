
"""
🚀 SpineDoc Aily CLI Adapter
============================
职责：专门供飞书 Aily 智能助手调度的精简版 CLI 入口。
架构：属于 Interaction Layer，作为 Backend Engine 与 Feishu Delivery 之间的桥接器。
"""

import os
import sys
import asyncio
from pathlib import Path
import typer
from rich.console import Console

# 🏛️ 架构锚定：确保能找到 backend 和 spine_interaction
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# 从 backend 导入核心引擎 (只导入，不修改)
from backend.app.services.spine_engine import SpineEngine
from backend.app.infra.memory.amem_adapter import AmemAdapter

# 从 interaction 导入交付工具
from spine_interaction.cards.builder import LarkCardBuilder
from backend.app.infra.lark_cli_reporter import LarkCliReporter

app = typer.Typer(help="SpineDoc Aily Bridge - 逻辑审计交互入口")
console = Console()

@app.command()
def audit(
    file_path: str = typer.Option(..., "--file", help="文档路径（支持本地或飞书云端 URL）"),
    query: str = typer.Option(..., "--query", help="审计质询问题"),
    chat_id: str = typer.Option(..., "--chat-id", help="飞书会话 ID，用于投射卡片")
):
    """
    执行逻辑审计并投射互动卡片到飞书。
    """
    async def _run():
        console.print(f"📡 [Aily] 接收到审计指令 | 目标: {file_path[:30]}... | 质询: {query}")
        
        # 1. 初始化引擎（核心业务逻辑）
        reporter = LarkCliReporter()
        memory = AmemAdapter()
        engine = SpineEngine(reporter=reporter, memory=memory)
        
        # 2. 调用引擎执行审计 (Backend Logic)
        console.print("⚙️ [Core] 正在执行逻辑编排...")
        # 导入文档
        ingest_res = await engine.ingest_document(file_path)
        doc_id = ingest_res["id"]
        
        # 执行联邦质证
        # 我们在这里捕获纯数据结果，然后交由 Interaction Layer 的 Builder 处理
        results = await engine.hybrid_ask(
            query=query, 
            doc_id=doc_id, 
            chat_id=chat_id, 
            sync_to_bitable=True
        )
        
        # 3. 结果交付 (Interaction Layer)
        console.print("🎨 [Interaction] 正在构建报告卡片...")
        # 注意：LarkCliReporter 内部已经集成了 LarkCardBuilder
        # 这里我们确保流程走通
        if results:
            console.print("✅ [Aily] 审计结果已成功通过云端投射。")
        else:
            console.print("⚠️ [Aily] 未能生成结论，请检查日志。")

    asyncio.run(_run())

if __name__ == "__main__":
    app()
