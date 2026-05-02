"""
Knowledge Graph Weaver — 知识图谱连接器

Design Philosophy:
    "关系不是数据录入，是冲突裁决后的结论"

    GraphWeaver 不负责发现关系，只负责执行 ConflictResolver 的裁决。
    只有当 ConflictResolver 在结果中明确声明了 proposed_relationships，
    GraphWeaver 才会物理化关系记录到 Git。

Core Responsibilities:
    1. 解析结果中的 proposed_relationships
    2. 验证关系两端 Chunk 是否存在
    3. 物理化关系记录到 Git
    4. 记录审计日志（指向结果 ID）

Usage:
    - Called after RetrievalCoordinator finishes synthesis
    - Independent of retrieval flow, failure doesn't block response
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
from uuid import UUID

from backend.app.services.knowledge.git_manager import get_git_manager

logger = logging.getLogger(__name__)


class GraphWeaverError(Exception):
    """GraphWeaver 异常"""
    pass


class GraphWeaver:
    """
    知识图谱连接器 — 严格执行 ConflictResolver 裁决 (Git 持久化版)

    职责：
    1. 解析结果中的 proposed_relationships
    2. 通过 GitManager 持久化关系快照
    3. 返回成功写入的关系列表
    """

    def __init__(self):
        self.git = get_git_manager()

    def weave_from_result(self, result: Dict) -> List:
        """
        从检索结果生成关系记录，通过 GitManager 持久化。

        Args:
            result: 检索结果，包含 id 和 proposed_relationships

        Returns:
            成功写入的关系列表
        """
        result_id = result.get("id")
        proposed = result.get("proposed_relationships", [])

        if not proposed:
            return []

        written = []
        for rel in proposed:
            rel_id = str(rel.get("id", f"{result_id}_{rel.get('source_chunk_id', '')}_{rel.get('target_chunk_id', '')}"))
            commit = self.git.commit_relationship(
                rel_id=rel_id,
                source_chunk_id=rel.get("source_chunk_id", ""),
                target_chunk_id=rel.get("target_chunk_id", ""),
                rel_type=rel.get("rel_type", "unknown"),
                strength=rel.get("strength", 0.5),
                description=rel.get("description"),
                verdict_id=result_id,
                operation="create",
                message=f"[graph] 知识图谱关系: {rel.get('rel_type', 'unknown')}"
            )
            if commit:
                written.append(rel)
                logger.info(f"关系写入 Git: {rel_id[:8]} ({rel.get('rel_type')})")

        return written

    weave_from_verdict = weave_from_result
