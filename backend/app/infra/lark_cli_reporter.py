"""
 Lark CLI Reporter - 飞书命令行报告员
========================================
职责：通过 lark-cli 命令行工具与飞书生态交互。
"""
import json
import logging
from typing import Dict, Any
from backend.app.core.interfaces import IFeishuReporter
from backend.app.infra.lark_cli_client import LarkCliClient

logger = logging.getLogger(__name__)

class LarkCliReporter(IFeishuReporter):
    def __init__(self, cli_path: str = "bin/lark-cli.exe"):
        self.cli_client = LarkCliClient(cli_path=cli_path)

    async def report_result(self, result: Dict[str, Any], chat_id: str) -> bool:
        """通过飞书发送纯文本报告"""
        text = result.get("text") or result.get("final_answer", "")
        card_json = {
            "config": {"wide_screen_mode": True},
            "elements": [{"tag": "div", "text": {"tag": "lark_md", "content": text[:5000]}}],
        }
        return await self.cli_client.send_interactive_card(chat_id, card_json)

    async def sync_asset(self, result: Dict[str, Any], evolution_logs: Dict[str, Any]) -> bool:
        from backend.app.core.config import settings

        knowledge_update = result.get("result_metadata", {}).get("knowledge_update", {})
        record_fields = {
            "审计问题": result.get("query", "未知查询"),
            "结论": result.get("text", result.get("final_answer", ""))[:5000],
            "置信度评分": result.get("result_metadata", {}).get("confidence", 0.0),
            "风险状态": " 高危" if knowledge_update else " 正常",
            "逻辑进化摘要": str(evolution_logs)[:2000]
        }

        if settings.FEISHU_BITABLE_TOKEN:
            sync_args = [
                "base", "+record-upsert",
                "--base-token", settings.FEISHU_BITABLE_TOKEN,
                "--table-id", settings.FEISHU_BITABLE_TABLE_ID,
                "--json", json.dumps(record_fields, ensure_ascii=False)
            ]
            await self.cli_client._run_command(sync_args)

        return True
