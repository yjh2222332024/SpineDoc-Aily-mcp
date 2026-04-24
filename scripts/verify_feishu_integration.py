
"""
🧪 SpineDoc Feishu Integration Verifier
=======================================
职责：验证逻辑引擎 -> 桥接器 -> 飞书 CLI -> 飞书云端的全链路闭环。
"""
import asyncio
import os
import sys
from pathlib import Path

# 路径锚定
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.app.services.spine_engine import SpineEngine
from backend.app.infra.lark_cli_reporter import LarkCliReporter
from backend.app.core.config import settings
from dotenv import load_dotenv

async def main():
    # 强制从当前目录的 .env 加载
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)
    
    print("🚀 [Verifier] 启动全链路集成验证...")
    
    # 1. 检查配置
    if not settings.FEISHU_DEFAULT_CHAT_ID:
        print("❌ 错误：未配置 FEISHU_DEFAULT_CHAT_ID。请先运行 ./bin/lark-cli.exe im +chat-search 获取。")
        return

    # 2. 初始化引擎（注入真实飞书手臂）
    reporter = LarkCliReporter(cli_path="bin/lark-cli.exe")
    engine = SpineEngine(reporter=reporter)

    # 3. 构造模拟判决书 (Verdict)
    mock_verdict = {
        "query": "检查《2026 校园挑战赛协议》的逻辑漏洞",
        "final_answer": (
            "经过联邦法庭质证，该协议存在 1 处高危逻辑断层：\n\n"
            "- **矛盾点**：第 5 页定义的‘参赛作品所有权’归属学生，但第 12 页‘授权条款’却声明版权归属飞书且不可撤销。\n"
            "- **裁决理由**：条款前后不一，存在逻辑闭环失效风险。\n"
            "- **置信度**：🔴 0.92 (逻辑强冲突)"
        ),
        "confidence": 0.92,
        "cited_galaxies": ["大赛官方协议.pdf", "法务通用模板"],
        "conflicts_resolved": [
            {"description": "版权归属条款前后矛盾", "severity": "CRITICAL"}
        ]
    }

    # 4. 执行报告动作
    print(f"📡 [Verifier] 尝试发送消息到群: {settings.FEISHU_DEFAULT_CHAT_ID}")
    msg_success = await reporter.report_verdict(mock_verdict, settings.FEISHU_DEFAULT_CHAT_ID)
    
    if msg_success:
        print("✅ [Verifier] 飞书群消息发送成功！")
    else:
        print("❌ [Verifier] 飞书群消息发送失败。")

    # 5. 执行同步到 Bitable
    if settings.FEISHU_BITABLE_TOKEN and settings.FEISHU_BITABLE_TABLE_ID:
        mock_evo_logs = {
            "node_id": "note_123",
            "action": "strengthen",
            "connected_to": "old_contract_v1",
            "reason": "检测到条款 A 与旧版合同存在强关联，已自动织网。"
        }
        print(f"💾 [Verifier] 尝试同步资产与进化日志到 Bitable...")
        db_success = await reporter.sync_asset(
            mock_verdict, 
            mock_evo_logs
        )
        if db_success:
            print("✅ [Verifier] 多维表格记录（含进化摘要）同步成功！")
        else:
            print("❌ [Verifier] 多维表格同步失败。")

if __name__ == "__main__":
    asyncio.run(main())
