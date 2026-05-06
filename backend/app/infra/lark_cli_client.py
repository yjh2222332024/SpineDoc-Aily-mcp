"""
 Lark CLI Client - 飞书命令行客户端
========================================
职责：原子化封装对 bin/lark-cli.exe 的调用，不包含业务逻辑。
"""
import json
import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

class LarkCliClient:
    def __init__(self, cli_path: str = "bin/lark-cli.exe"):
        # 寻找相对于项目根目录的路径
        self.cli_path = str(Path(cli_path).absolute())
        if not os.path.exists(self.cli_path):
            # 兼容性处理：尝试在当前工作目录寻找
            self.cli_path = str(Path(os.getcwd()) / cli_path)

    async def _run_command(self, args: List[str]) -> (bool, str):
        from backend.app.core.config import settings
        
        # 环境变量对齐：lark-cli 常用 LARK_APP_ID 或通过 config init
        # 架构师指令：我们直接通过环境变量注入，确保原子化操作无需事先 login
        env = os.environ.copy()
        if settings.FEISHU_APP_ID:
            env["LARK_APP_ID"] = settings.FEISHU_APP_ID
            env["FEISHU_APP_ID"] = settings.FEISHU_APP_ID
        if settings.FEISHU_APP_SECRET:
            env["LARK_APP_SECRET"] = settings.FEISHU_APP_SECRET
            env["FEISHU_APP_SECRET"] = settings.FEISHU_APP_SECRET

        cmd = [self.cli_path] + args
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                return True, stdout.decode().strip()
            else:
                error_msg = stderr.decode().strip()
                logger.error(f" [LarkCLI] 命令失败: {error_msg}")
                return False, error_msg
        except Exception as e:
            logger.error(f" [LarkCLI] 执行异常: {e}")
            return False, str(e)

    async def download_drive_file(self, file_token: str, output_path: str) -> bool:
        """调用 lark-cli 下载飞书云端文件"""
        args = [
            "drive", "+download",
            "--file-token", file_token,
            "--output", output_path,
            "--overwrite"
        ]
        success, _ = await self._run_command(args)
        return success

    async def send_interactive_card(self, chat_id: str, card_json: dict) -> bool:
        """发送互动卡片"""
        args = [
            "im", "+messages-send",
            "--chat-id", chat_id,
            "--msg-type", "interactive",
            "--content", json.dumps(card_json, ensure_ascii=False)
        ]
        success, _ = await self._run_command(args)
        return success
