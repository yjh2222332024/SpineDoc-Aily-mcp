"""
🧬 代谢管理器 (Metabolism Manager)
===================================
负责知识库的新陈代谢：应用裁决 → Git 提交 → 历史溯源 → 回滚

职责分离：
- SpineEngine: 只负责问答分发
- FederatedCourt: 只负责裁决
- MetabolismManager: 只负责知识更新（Git 事务）
"""

import logging
from typing import List, Dict, Optional
from backend.app.core.config import settings
from backend.app.services.knowledge.git_manager import get_git_manager, GitManager

logger = logging.getLogger(__name__)


class MetabolismManager:
    """
    🧬 代谢管理器

    职责：
    1. 应用法庭裁决到知识库（Git 提交）
    2. 查询 Chunk 历史
    3. 回滚到指定版本
    """

    def __init__(self):
        self.git_manager = get_git_manager()

    async def apply(self, delta: Dict) -> Dict[str, str]:
        """
        应用知识增量到 Git

        Args:
            delta: {
                "has_delta": bool,
                "updated_chunks": [...],
                "commit_message": str
            }

        Returns:
            {chunk_id: commit_hash}
        """
        if not delta.get("has_delta"):
            return {}

        results = {}
        print(f"🧬 [Metabolism] 正在应用知识增量...")

        for chunk_change in delta.get("updated_chunks", []):
            chunk_id = chunk_change.get("chunk_id")
            if not chunk_id:
                continue

            # 提交到 Git
            content = chunk_change.get("new_content") or chunk_change.get("old_content", "")
            metadata = chunk_change.get("metadata", {})
            message = delta.get("commit_message", "知识库更新")

            commit_hash = self.git_manager.commit_chunk(
                chunk_id=chunk_id,
                content=content,
                metadata=metadata,
                message=message
            )

            if commit_hash:
                results[chunk_id] = commit_hash[:settings.CONTEXT_COMMIT_DOC_ID_PREFIX]
                print(f"  ✓ Chunk {chunk_id[:settings.CONTEXT_COMMIT_DOC_ID_PREFIX]} → git:{commit_hash[:settings.CONTEXT_COMMIT_DOC_ID_PREFIX]}")
            else:
                print(f"  ⚠️ Chunk {chunk_id[:settings.CONTEXT_COMMIT_DOC_ID_PREFIX]} 无变更，跳过提交")

        return results

    def history(self, chunk_id: str, limit: int = 20) -> List[Dict]:
        """
        查询 Chunk 的 Git 历史

        Args:
            chunk_id: Chunk ID
            limit: 返回数量上限

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

    def revert(self, chunk_id: str, commit_hash: str) -> bool:
        """
        回滚 Chunk 到指定提交

        Args:
            chunk_id: Chunk ID
            commit_hash: 提交哈希

        Returns:
            是否成功
        """
        return self.git_manager.revert_chunk(chunk_id, commit_hash)

    def diff(self, chunk_id: str, old_commit: str, new_commit: str) -> str:
        """
        比较两个提交之间的差异

        Args:
            chunk_id: Chunk ID
            old_commit: 旧提交哈希
            new_commit: 新提交哈希

        Returns:
            diff 文本
        """
        return self.git_manager.diff_chunks(chunk_id, old_commit, new_commit)


# 全局单例
_global_metabolism: Optional[MetabolismManager] = None


def get_metabolism_manager() -> MetabolismManager:
    """获取全局 MetabolismManager 实例"""
    global _global_metabolism
    if _global_metabolism is None:
        _global_metabolism = MetabolismManager()
    return _global_metabolism
