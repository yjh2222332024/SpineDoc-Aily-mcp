"""
SpineDoc 影子持久化同步器 (ShadowSynchronizer) - V1.0
===================================================
职责：负责将本地处理的逻辑脊梁与切片实时同步至飞书云文档。
复用：LarkCliReporter 的执行引擎，确保生态一致性。
"""
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional
from backend.app.infra.lark_cli_reporter import LarkCliReporter

logger = logging.getLogger(__name__)

class LarkShadowSynchronizer(LarkCliReporter):
    def __init__(self, cli_path: str = "bin/lark-cli.exe"):
        super().__init__(cli_path)
        self.current_doc_token = None

    async def init_document(self, title: str) -> Optional[str]:
        """
        创建一个空白影子文档，作为持久化容器。
        """
        # 利用 docs +create 接口，创建带标题的空文档
        args = [
            "docs", "+create",
            "--title", f"🦴 [SpineDoc-Shadow] {title}",
            "--markdown", f"# {title}\n\n> 此文档由 SpineDoc 逻辑镜像自动生成。"
        ]
        
        # 捕获 stdout 拿回 token
        cmd = [self.cli_path] + args
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode == 0:
                resp = json.loads(stdout.decode())
                self.current_doc_token = resp.get("data", {}).get("doc_id")
                logger.info(f" [ShadowSync] 影子文档创建成功: {self.current_doc_token}")
                return self.current_doc_token
            else:
                logger.error(f" [ShadowSync] 文档创建失败: {stderr.decode()}")
                return None
        except Exception as e:
            logger.error(f" [ShadowSync] 初始化异常: {e}")
            return None

    async def push_blocks(self, blocks: List[Dict[str, Any]], doc_format: str = "markdown"):
        """
        批量推送逻辑块（支持 Markdown 或 XML 格式）。
        """
        if not self.current_doc_token:
            return False

        content = ""
        if doc_format == "markdown":
            for b in blocks:
                if b.get("type") == "heading":
                    level = b.get("level", 1)
                    prefix = "#" * level
                    content += f"{prefix} {b['title']}\n\n"
                else:
                    content += f"{b.get('content', '')}\n\n"
        else:
            # XML 模式，直接拼接原始内容
            content = "".join([b.get("content", "") for b in blocks])

        if not content: return True

        args = [
            "docs", "+update",
            "--doc", self.current_doc_token,
            "--markdown" if doc_format == "markdown" else "--content", content,
            "--mode", "append"
        ]
        
        # 如果是 XML，需要显式指定格式
        if doc_format == "xml":
            args.extend(["--doc-format", "xml"])
        
        return await self._run_command(args)

    async def add_logic_comment(self, block_index: int, comment: str):
        """
        在特定的逻辑块旁边打上审计批注。
        """
        # 这一步需要 block_id，未来通过解析 docs +fetch 的 JSON 获得。
        # 目前作为占位符，记录逻辑确权的意图。
        pass

# 全局同步器单例
shadow_sync = LarkShadowSynchronizer()
