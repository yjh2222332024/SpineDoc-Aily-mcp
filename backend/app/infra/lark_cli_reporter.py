
"""
🏛️ Lark CLI Reporter - 飞书命令行报告员
========================================
职责：通过 lark-cli 命令行工具与飞书生态交互。
"""
import json
import asyncio
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List
from backend.app.core.interfaces import IFeishuReporter
from backend.app.infra.lark_card_builder import LarkCardBuilder

logger = logging.getLogger(__name__)

class LarkCliReporter(IFeishuReporter):
    def __init__(self, cli_path: str = "bin/lark-cli.exe"):
        self.cli_path = str(Path(cli_path).absolute())
        self.card_builder = LarkCardBuilder()

    async def _run_command(self, args: List[str]) -> bool:
        # ... (保持原有逻辑不变)
        cmd = [self.cli_path] + args
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                return True
            else:
                logger.error(f"❌ [LarkCLI] 命令失败: {stderr.decode()}")
                return False
        except Exception as e:
            logger.error(f"❌ [LarkCLI] 执行异常: {e}")
            return False

    async def report_result(self, result: Dict[str, Any], chat_id: str) -> bool:
        """通过飞书发送精美的互动卡片报告"""
        # 优先使用 AilyPresenter 格式的卡片（白盒化程度高），否则回退到 LarkCardBuilder
        if result.get("interactive_card"):
            card_json = result["interactive_card"]
        else:
            card_json = self.card_builder.build_result_card(result)

        # 🚀 [V52.12] 修复参数：使用 --msg-type interactive 和 --content
        args = [
            "im", "+messages-send",
            "--chat-id", chat_id,
            "--msg-type", "interactive",
            "--content", json.dumps(card_json, ensure_ascii=False)
        ]
        return await self._run_command(args)

    async def sync_asset(self, result: Dict[str, Any], evolution_logs: Dict[str, Any]) -> bool:
        # ... (同步 Bitable 逻辑不变)
        from backend.app.core.config import settings

        # 构造 Bitable 记录
        knowledge_update = result.get("result_metadata", {}).get("knowledge_update", {})
        record_fields = {
            "审计问题": result.get("query", "未知查询"),
            "结论": result.get("text", result.get("final_answer", ""))[:5000],
            "置信度评分": result.get("result_metadata", {}).get("confidence", 0.0),
            "风险状态": "🔴 高危" if knowledge_update else "🟢 正常",
            "逻辑进化摘要": str(evolution_logs)[:2000]
        }

        if settings.FEISHU_BITABLE_TOKEN:
            sync_args = [
                "base", "+record-upsert",
                "--base-token", settings.FEISHU_BITABLE_TOKEN,
                "--table-id", settings.FEISHU_BITABLE_TABLE_ID,
                "--json", json.dumps(record_fields, ensure_ascii=False)
            ]
            await self._run_command(sync_args)

        # 2. 如果有进化日志，额外发送一张进化卡片
        if evolution_logs and evolution_logs.get("details"):
            evo_card = self.card_builder.build_evolution_card(evolution_logs)
            chat_id = settings.FEISHU_DEFAULT_CHAT_ID
            if chat_id:
                args = [
                    "im", "+messages-send",
                    "--chat-id", chat_id,
                    "--msg-type", "interactive",
                    "--content", json.dumps(evo_card, ensure_ascii=False)
                ]
                return await self._run_command(args)

        return True
