"""
📜 Git 版本控制服务
====================
封装 Git 版本管理操作，供 SpineEngine 调用。
"""

import asyncio
from typing import List, Dict, Optional
from backend.app.services.knowledge.git_manager import get_git_manager, GitManager
from backend.app.services.knowledge.metabolism_manager import get_metabolism_manager, MetabolismManager


class GitVersionControl:
    """
    📜 Git 版本控制服务

    职责：
    1. 查询 Chunk 历史
    2. 查看 Chunk 内容（当前/历史版本）
    3. 回滚 Chunk
    4. 比较差异
    """

    def __init__(self):
        self.git_manager = get_git_manager()
        self.metabolism_manager = get_metabolism_manager()
        self._write_lock = asyncio.Lock()  #  [V52.9] 并发主权锁，防止多用户同时修改仓库

    def get_chunk_history(self, chunk_id: str, limit: int = 20) -> List[Dict]:
        # ... (原有逻辑保持不变)
        """
        获取 Chunk 的 Git 历史

        Args:
            chunk_id: Chunk ID
            limit: 返回数量

        Returns:
            提交记录列表
        """
        commits = self.git_manager.get_chunk_history(chunk_id, limit)
        return [
            {
                "hash": c.hash,
                "short_hash": c.short_hash,
                "message": c.message,
                "timestamp": c.timestamp.isoformat(),
                "author": c.author
            }
            for c in commits
        ]

    def get_chunk_content(
        self,
        chunk_id: str,
        commit_hash: Optional[str] = None
    ) -> Optional[Dict]:
        """
        获取 Chunk 内容（当前版本或历史版本）

        Args:
            chunk_id: Chunk ID
            commit_hash: 可选，指定历史版本

        Returns:
            Chunk 数据或 None
        """
        if commit_hash:
            # 查看历史版本
            return self.git_manager.get_chunk_at_commit(chunk_id, commit_hash)
        else:
            # 查看当前版本
            import json
            from pathlib import Path

            chunks_dir = self.git_manager.repo_path / "chunks"
            filepath = chunks_dir / f"{chunk_id}.json"

            if not filepath.exists():
                return None

            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)

    def revert_chunk(self, chunk_id: str, commit_hash: str) -> bool:
        """
        回滚 Chunk 到指定提交

        Args:
            chunk_id: Chunk ID
            commit_hash: 提交哈希

        Returns:
            是否成功
        """
        return self.metabolism_manager.revert(chunk_id, commit_hash)

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
        return self.git_manager.diff_chunks(chunk_id, old_commit, new_commit)

    async def apply_knowledge_delta(self, delta: Dict) -> Dict[str, str]:
        """
        应用知识增量到 Git (带并发锁保护)
        """
        async with self._write_lock:
            return await self.metabolism_manager.apply(delta)


# 全局单例
_global_git_version_control: Optional[GitVersionControl] = None


def get_git_version_control() -> GitVersionControl:
    """获取 GitVersionControl 实例"""
    global _global_git_version_control
    if _global_git_version_control is None:
        _global_git_version_control = GitVersionControl()
    return _global_git_version_control
