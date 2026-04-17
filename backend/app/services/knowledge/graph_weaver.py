"""
GraphWeaver - 逻辑织网缝合者

设计哲学:
    "关联不是数据录入，是审判后的质证结论"

    GraphWeaver 不负责发现关系，只负责执行 Moderator 的裁决。
    只有当 Moderator 在 Verdict 中明确声明了 proposed_relationships，
    GraphWeaver 才会物理化 ChunkRelationship 记录。

核心职责:
    1. 解析 Verdict 中的 proposed_relationships
    2. 验证关系两端 Chunk 是否存在
    3. 物理化 ChunkRelationship 记录
    4. 记录审计日志（指向 Verdict ID）

使用场景:
    - FederatedCourt 审判结束后调用
    - 独立于检索流，即使失败也不阻塞答复

作者：SpineDoc Team
日期：2026-04-16
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
from uuid import UUID

from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from backend.app.core.models import ChunkRelationship, RelationshipType, Chunk
from backend.app.services.knowledge.git_manager import get_git_manager

logger = logging.getLogger(__name__)


class GraphWeaverError(Exception):
    """GraphWeaver 异常"""
    pass


class GraphWeaver:
    """
    逻辑织网缝合者 - 严格执行 Moderator 裁决

    使用示例:
        weaver = GraphWeaver(db_session)
        weaver.weave_from_verdict(verdict_dict)

    核心方法:
        weave_from_verdict(): 从裁决书生成关系
        _validate_chunks(): 验证 Chunk 存在性
        _create_relationship(): 创建单条关系记录
    """

    def __init__(self, db_session: Session):
        """
        初始化 GraphWeaver

        Args:
            db_session: SQLAlchemy 数据库会话
        """
        self.db = db_session
        self.git = get_git_manager()  # 🕸️ [V7.0] Git 版本控制

    def weave_from_verdict(self, verdict: Dict) -> List[ChunkRelationship]:
        """
        从裁决书生成关系记录

        Verdict 结构:
        {
            "id": "verdict-uuid",
            "proposed_relationships": [
                {
                    "source_chunk_id": "chunk-uuid-1",
                    "target_chunk_id": "chunk-uuid-2",
                    "rel_type": "contradiction",  # 必须是 RelationshipType 枚举值
                    "strength": 0.95,
                    "description": "两个 Chunk 在密钥长度描述上存在直接矛盾",
                    "evidence": "Chunk A 说 128 位，Chunk B 说 64 位"
                }
            ]
        }

        Args:
            verdict: 裁决书字典

        Returns:
            生成的关系记录列表

        Raises:
            GraphWeaverError: 当关系声明无效时抛出异常
        """
        verdict_id = verdict.get("id")
        proposed = verdict.get("proposed_relationships", [])

        if not proposed:
            logger.info(f"Verdict {verdict_id}: 无关系声明，跳过织网")
            return []

        logger.info(f"Verdict {verdict_id}: 开始缝合 {len(proposed)} 条关系")

        created_relationships = []
        errors = []

        for rel in proposed:
            try:
                # 严格验证：大法官必须明确声明所有必要字段
                relationship = self._create_relationship(
                    source_chunk_id=rel.get("source_chunk_id"),
                    target_chunk_id=rel.get("target_chunk_id"),
                    rel_type=rel.get("rel_type"),
                    strength=rel.get("strength", 1.0),
                    description=rel.get("description"),
                    verdict_id=verdict_id
                )
                created_relationships.append(relationship)
                logger.info(f"  ✓ 关系创建成功：{rel.get('source_chunk_id')[:8]} -> {rel.get('target_chunk_id')[:8]} ({rel.get('rel_type')})")

            except GraphWeaverError as e:
                errors.append({
                    "relationship": rel,
                    "error": str(e)
                })
                logger.warning(f"  ⚠ 关系创建失败：{e}")

        # 统计报告
        success_count = len(created_relationships)
        fail_count = len(errors)
        logger.info(f"Verdict {verdict_id}: 织网完成 - 成功 {success_count}, 失败 {fail_count}")

        if errors and success_count == 0:
            raise GraphWeaverError(f"所有关系创建失败：{errors}")

        return created_relationships

    def _create_relationship(
        self,
        source_chunk_id: str,
        target_chunk_id: str,
        rel_type: str,
        strength: float,
        description: Optional[str],
        verdict_id: Optional[str]
    ) -> ChunkRelationship:
        """
        创建单条关系记录（严格执行验证）

        验证规则:
          1. source_chunk_id 必须存在
          2. target_chunk_id 必须存在
          3. rel_type 必须是 RelationshipType 枚举值
          4. strength 必须在 [0.0, 1.0] 范围内
          5. 不能自环（source != target）

        Args:
            source_chunk_id: 源 Chunk ID
            target_chunk_id: 目标 Chunk ID
            rel_type: 关系类型（必须是枚举值）
            strength: 关系强度
            description: 关系描述
            verdict_id: 触发此关系的 Verdict ID

        Returns:
            创建的 ChunkRelationship 记录

        Raises:
            GraphWeaverError: 验证失败时抛出
        """
        # === 严格验证阶段 ===

        # 1. 验证关系类型（必须是枚举值）
        try:
            relationship_type = RelationshipType(rel_type)
        except ValueError:
            valid_types = [t.value for t in RelationshipType]
            raise GraphWeaverError(
                f"无效的关系类型 '{rel_type}'，必须是以下之一：{valid_types}"
            )

        # 2. 验证强度范围
        if not (0.0 <= strength <= 1.0):
            raise GraphWeaverError(
                f"关系强度 {strength} 超出范围 [0.0, 1.0]"
            )

        # 3. 验证不能自环
        if source_chunk_id == target_chunk_id:
            raise GraphWeaverError(
                f"不允许自环关系：{source_chunk_id}"
            )

        # 4. 验证 Chunk 存在性
        self._validate_chunk_exists(source_chunk_id)
        self._validate_chunk_exists(target_chunk_id)

        # === 物理化阶段 ===

        try:
            relationship = ChunkRelationship(
                source_chunk_id=source_chunk_id,
                target_chunk_id=target_chunk_id,
                rel_type=relationship_type,
                strength=strength,
                description=description,
                verdict_id=verdict_id,
                created_by="GraphWeaver"
            )

            self.db.add(relationship)
            self.db.commit()
            self.db.refresh(relationship)

            # 🕸️ [V7.0] 同步提交到 Git（关系网络版本控制）
            try:
                self.git.commit_relationship(
                    rel_id=str(relationship.id),
                    source_chunk_id=source_chunk_id,
                    target_chunk_id=target_chunk_id,
                    rel_type=relationship_type.value,
                    strength=strength,
                    description=description,
                    verdict_id=verdict_id,
                    operation="create",
                    message=f"[create] {relationship_type.value}: {source_chunk_id[:8]} -> {target_chunk_id[:8]}"
                )
            except Exception as git_err:
                # Git 提交失败不影响数据库操作，仅记录警告
                logger.warning(f"Git 提交失败：{git_err}")

            logger.info(
                f"关系已物理化：{source_chunk_id[:8]} -[{relationship_type.value}]-> {target_chunk_id[:8]} "
                f"(strength={strength}, verdict={verdict_id[:8] if verdict_id else 'N/A'})"
            )

            return relationship

        except IntegrityError as e:
            self.db.rollback()
            # 重复关系（已存在）
            raise GraphWeaverError(
                f"关系已存在：{source_chunk_id} -> {target_chunk_id} ({rel_type})"
            ) from e

    def _validate_chunk_exists(self, chunk_id: str) -> None:
        """
        验证 Chunk 是否存在

        Args:
            chunk_id: Chunk ID

        Raises:
            GraphWeaverError: Chunk 不存在时抛出
        """
        statement = select(Chunk).where(Chunk.id == chunk_id)
        chunk = self.db.exec(statement).first()

        if not chunk:
            raise GraphWeaverError(f"Chunk 不存在：{chunk_id}")

    def update_relationship(
        self,
        rel_id: str,
        strength: Optional[float] = None,
        description: Optional[str] = None,
        verdict_id: Optional[str] = None
    ) -> Optional[ChunkRelationship]:
        """
        更新关系（同步 Git）

        Args:
            rel_id: 关系 ID
            strength: 新的关系强度
            description: 新的关系描述
            verdict_id: 新的 Verdict ID

        Returns:
            更新后的关系记录，或 None
        """
        statement = select(ChunkRelationship).where(ChunkRelationship.id == rel_id)
        relationship = self.db.exec(statement).first()

        if not relationship:
            raise GraphWeaverError(f"关系不存在：{rel_id}")

        # 更新字段
        old_data = {
            "strength": relationship.strength,
            "description": relationship.description,
            "verdict_id": relationship.verdict_id
        }

        if strength is not None:
            relationship.strength = strength
        if description is not None:
            relationship.description = description
        if verdict_id is not None:
            relationship.verdict_id = verdict_id

        self.db.add(relationship)
        self.db.commit()
        self.db.refresh(relationship)

        # 🕸️ [V7.0] 同步提交到 Git
        try:
            self.git.commit_relationship(
                rel_id=rel_id,
                source_chunk_id=relationship.source_chunk_id,
                target_chunk_id=relationship.target_chunk_id,
                rel_type=relationship.rel_type.value,
                strength=relationship.strength,
                description=relationship.description,
                verdict_id=relationship.verdict_id,
                operation="update",
                message=f"[update] 关系 {rel_id[:8]}: strength {old_data['strength']} -> {relationship.strength}"
            )
        except Exception as git_err:
            logger.warning(f"Git 提交失败：{git_err}")

        logger.info(f"关系已更新：{rel_id[:8]}")
        return relationship

    def delete_relationship(self, rel_id: str) -> bool:
        """
        删除关系（同步 Git）

        Args:
            rel_id: 关系 ID

        Returns:
            是否成功删除
        """
        statement = select(ChunkRelationship).where(ChunkRelationship.id == rel_id)
        relationship = self.db.exec(statement).first()

        if not relationship:
            logger.warning(f"关系不存在：{rel_id}")
            return False

        # 记录信息用于 Git 提交
        rel_info = {
            "source_chunk_id": relationship.source_chunk_id,
            "target_chunk_id": relationship.target_chunk_id,
            "rel_type": relationship.rel_type.value
        }

        # 删除数据库记录
        self.db.delete(relationship)
        self.db.commit()

        # 🕸️ [V7.0] 同步提交到 Git
        try:
            self.git.commit_relationship(
                rel_id=rel_id,
                source_chunk_id=rel_info["source_chunk_id"],
                target_chunk_id=rel_info["target_chunk_id"],
                rel_type=rel_info["rel_type"],
                strength=0,
                description=None,
                verdict_id=None,
                operation="delete",
                message=f"[delete] 删除关系 {rel_id[:8]}: {rel_info['source_chunk_id'][:8]} -[{rel_info['rel_type']}]-> {rel_info['target_chunk_id'][:8]}"
            )
        except Exception as git_err:
            logger.warning(f"Git 提交失败：{git_err}")

        logger.info(f"关系已删除：{rel_id[:8]}")
        return True

    def list_relationships_by_chunk(
        self,
        chunk_id: str,
        rel_type: Optional[str] = None,
        direction: str = "both"
    ) -> List[ChunkRelationship]:
        """
        查询指定 Chunk 的关系

        Args:
            chunk_id: Chunk ID
            rel_type: 筛选关系类型（None 表示全部）
            direction: 查询方向 ("outgoing", "incoming", "both")

        Returns:
            关系记录列表
        """
        if direction == "outgoing":
            # 查询出边
            statement = select(ChunkRelationship).where(
                ChunkRelationship.source_chunk_id == chunk_id
            )
        elif direction == "incoming":
            # 查询入边
            statement = select(ChunkRelationship).where(
                ChunkRelationship.target_chunk_id == chunk_id
            )
        else:
            # 双向
            statement = select(ChunkRelationship).where(
                (ChunkRelationship.source_chunk_id == chunk_id) |
                (ChunkRelationship.target_chunk_id == chunk_id)
            )

        if rel_type:
            statement = statement.where(
                ChunkRelationship.rel_type == RelationshipType(rel_type)
            )

        relationships = self.db.exec(statement).all()
        return list(relationships)

    def get_relationship_network(
        self,
        chunk_id: str,
        max_depth: int = 2
    ) -> Dict:
        """
        获取 Chunk 的关系网络（用于可视化）

        Args:
            chunk_id: 起始 Chunk ID
            max_depth: 最大遍历深度

        Returns:
            网络字典 {nodes: [...], edges: [...]}
        """
        nodes = {chunk_id}
        edges = []

        # BFS 遍历
        current_level = [chunk_id]
        depth = 0

        while depth < max_depth and current_level:
            next_level = []
            for cid in current_level:
                relationships = self.list_relationships_by_chunk(cid)
                for rel in relationships:
                    # 确定另一端节点
                    other_id = rel.target_chunk_id if rel.source_chunk_id == cid else rel.source_chunk_id

                    if other_id not in nodes:
                        nodes.add(other_id)
                        next_level.append(other_id)

                    edges.append({
                        "source": rel.source_chunk_id,
                        "target": rel.target_chunk_id,
                        "type": rel.rel_type.value,
                        "strength": rel.strength,
                        "description": rel.description
                    })

            current_level = next_level
            depth += 1

        return {
            "nodes": list(nodes),
            "edges": edges
        }
