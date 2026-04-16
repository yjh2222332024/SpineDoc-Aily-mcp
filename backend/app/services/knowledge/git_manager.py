"""
📜 Git 版本管理器 (精简版)
============================
为知识库提供 Git 溯源能力，不干预 CRUD 流程。

核心设计：
1. CRUD 操作直接更新数据库
2. Git 异步提交快照（用于溯源/回滚）
3. 用户可通过 CLI 查看历史/回滚
"""

import os
import json
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class GitCommit:
    """Git 提交记录"""
    hash: str
    short_hash: str
    message: str
    timestamp: datetime
    author: str


class GitManager:
    """
    📜 Git 版本管理器（精简版）

    职责：
    1. 初始化 Git 仓库（backend/storage/git-repo）
    2. 提交 Chunk 快照
    3. 查询历史/回滚
    """

    def __init__(
        self,
        repo_path: Optional[str] = None,
        author_name: str = "SpineDoc",
        author_email: str = "spine@local"
    ):
        """
        Args:
            repo_path: Git 仓库路径，默认 backend/storage/git-repo
        """
        if repo_path is None:
            base_dir = Path(__file__).parent.parent.parent
            repo_path = str(base_dir / "storage" / "git-repo")

        self.repo_path = Path(repo_path)
        self.author_name = author_name
        self.author_email = author_email
        self._ensure_repo()

    def _ensure_repo(self):
        """确保仓库存在且已初始化"""
        self.repo_path.mkdir(parents=True, exist_ok=True)

        git_dir = self.repo_path / ".git"
        if not git_dir.exists():
            self._git("init")
            self._git("config", "user.name", self.author_name)
            self._git("config", "user.email", self.author_email)
            logger.info(f"📜 Git 仓库已初始化：{self.repo_path}")

    def _git(self, *args, cwd=None) -> str:
        """运行 git 命令"""
        cmd = ["git"] + list(args)
        result = subprocess.run(
            cmd,
            cwd=cwd or self.repo_path,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()

    def commit_chunk(
        self,
        chunk_id: str,
        content: str,
        metadata: Optional[Dict] = None,
        message: str = ""
    ) -> Optional[str]:
        """
        提交 Chunk 快照到 Git

        Args:
            chunk_id: Chunk ID
            content: 文本内容
            metadata: 元数据（页码、breadcrumb 等）
            message: 提交消息

        Returns:
            commit_hash 或 None（无变更）
        """
        chunks_dir = self.repo_path / "chunks"
        chunks_dir.mkdir(exist_ok=True)

        # 🚑 [FIX] Windows 文件名 sanitization: 替换非法字符 (: \ / ? * | " < >)
        # 联网证据的 chunk_id 可能包含 URL，需要清理
        safe_chunk_id = chunk_id.replace(":", "_").replace("/", "_").replace("\\", "_")
        safe_chunk_id = safe_chunk_id.replace("?", "_").replace("*", "_")
        safe_chunk_id = safe_chunk_id.replace("|", "_").replace("<", "_").replace(">", "_")
        safe_chunk_id = safe_chunk_id.replace('"', "_")

        filepath = chunks_dir / f"{safe_chunk_id}.json"

        # 检查是否有变更
        old_content = None
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                old_content = old_data.get("content")

        if old_content == content:
            logger.debug(f"Chunk {chunk_id[:settings.CONTEXT_COMMIT_DOC_ID_PREFIX]} 无变更，跳过提交")
            return None

        # 写入新快照
        data = {
            "id": chunk_id,
            "content": content,
            "metadata": metadata or {},
            "updated_at": datetime.utcnow().isoformat()
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Git 提交
        self._git("add", str(filepath))

        status = self._git("status", "--porcelain")
        if not status.strip():
            return None

        commit_msg = message or f"更新 Chunk {chunk_id[:settings.CONTEXT_COMMIT_DOC_ID_PREFIX]}"
        self._git("commit", "-m", commit_msg)

        commit_hash = self._git("rev-parse", "HEAD")
        logger.info(f"📜 Git 提交成功：{commit_hash[:settings.CONTEXT_COMMIT_DOC_ID_PREFIX]} - {commit_msg}")

        return commit_hash

    def get_chunk_history(self, chunk_id: str, limit: int = 20) -> List[GitCommit]:
        """
        获取 Chunk 的 Git 历史

        Args:
            chunk_id: Chunk ID
            limit: 返回数量

        Returns:
            提交记录列表
        """
        filepath = f"chunks/{chunk_id}.json"
        output = self._git(
            "log", f"-n{limit}", "--pretty=format:%H|%h|%s|%ai|%an",
            "--", filepath
        )

        commits = []
        for line in output.split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 4)
            if len(parts) == 5:
                commits.append(GitCommit(
                    hash=parts[0],
                    short_hash=parts[1],
                    message=parts[2],
                    timestamp=datetime.fromisoformat(parts[3]),
                    author=parts[4]
                ))

        return commits

    def get_chunk_at_commit(self, chunk_id: str, commit_hash: str) -> Optional[Dict]:
        """
        获取 Chunk 在指定提交时的内容

        Args:
            chunk_id: Chunk ID
            commit_hash: 提交哈希

        Returns:
            Chunk 数据或 None
        """
        filepath = f"chunks/{chunk_id}.json"
        try:
            content = self._git("show", f"{commit_hash}:{filepath}")
            return json.loads(content)
        except subprocess.CalledProcessError:
            return None

    def revert_chunk(self, chunk_id: str, commit_hash: str) -> bool:
        """
        回滚 Chunk 到指定提交

        Args:
            chunk_id: Chunk ID
            commit_hash: 提交哈希

        Returns:
            是否成功
        """
        filepath = f"chunks/{chunk_id}.json"

        try:
            # 恢复文件到指定版本
            self._git("checkout", commit_hash, "--", filepath)

            # 提交回滚
            self._git("add", str(self.repo_path / filepath))
            self._git("commit", "-m", f"revert: 回滚 Chunk {chunk_id[:settings.CONTEXT_COMMIT_DOC_ID_PREFIX]} 到 {commit_hash[:settings.CONTEXT_COMMIT_DOC_ID_PREFIX]}")

            logger.info(f"✅ Chunk {chunk_id[:settings.CONTEXT_COMMIT_DOC_ID_PREFIX]} 已回滚到 {commit_hash[:settings.CONTEXT_COMMIT_DOC_ID_PREFIX]}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"回滚失败：{e}")
            return False

    def diff_chunks(
        self,
        chunk_id: str,
        old_commit: str,
        new_commit: str
    ) -> str:
        """
        比较 Chunk 在两个提交之间的差异

        Args:
            chunk_id: Chunk ID
            old_commit: 旧提交
            new_commit: 新提交

        Returns:
            diff 文本
        """
        filepath = f"chunks/{chunk_id}.json"
        return self._git("diff", old_commit, new_commit, "--", filepath)


# 全局单例
_global_manager: Optional[GitManager] = None


def get_git_manager(repo_path: Optional[str] = None) -> GitManager:
    """获取 GitManager 实例"""
    global _global_manager
    if _global_manager is None:
        _global_manager = GitManager(repo_path)
    return _global_manager
