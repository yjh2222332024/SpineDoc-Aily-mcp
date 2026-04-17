from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, JSON
from sqlalchemy.dialects.postgresql import JSONB # 🚀 保持 JSONB 兼容性
from backend.app.core.config import settings 

class ProcessingStatus(str, Enum):
    """文档处理状态枚举"""
    PENDING = "pending"
    PARTIAL = "partial"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# --- 🚀 [V1.0] 基础关联与用户体系 ---

class DocumentTagLink(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    document_id: UUID = Field(foreign_key="document.id", primary_key=True)
    tag_id: UUID = Field(foreign_key="tag.id", primary_key=True)

class User(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    workspaces: List["Workspace"] = Relationship(back_populates="owner")
    event_logs: List["EventLog"] = Relationship(back_populates="user")

class Workspace(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    owner_id: UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    owner: User = Relationship(back_populates="workspaces")
    documents: List["Document"] = Relationship(back_populates="workspace")
    folders: List["Folder"] = Relationship(back_populates="workspace")

class Folder(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    parent_id: Optional[UUID] = Field(default=None, foreign_key="folder.id")
    workspace_id: UUID = Field(foreign_key="workspace.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    workspace: Workspace = Relationship(back_populates="folders")
    parent: Optional["Folder"] = Relationship(back_populates="children", sa_relationship_kwargs={"remote_side": "Folder.id"})
    children: List["Folder"] = Relationship(back_populates="parent")
    documents: List["Document"] = Relationship(back_populates="folder")

class Tag(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    color: str = "#808080"
    workspace_id: UUID = Field(foreign_key="workspace.id")
    documents: List["Document"] = Relationship(back_populates="tags", link_model=DocumentTagLink)

# --- 🚀 [V5.0] 知识星系核心架构 (作为新表存在，不影响旧表物理结构) ---

class Galaxy(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(unique=True) # 🚀 移除 index=True，保持简洁，避免索引冲突
    description: str
    centroid_embedding: List[float] = Field(sa_column=Column(Vector(settings.EMBEDDING_DIMENSION)))
    member_count: int = Field(default=0) # 🚀 记录成员总数，支撑人口加权演化
    created_at: datetime = Field(default_factory=datetime.utcnow)
    document_links: List["DocumentGalaxyLink"] = Relationship(back_populates="galaxy")

class DocumentGalaxyLink(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    document_id: UUID = Field(foreign_key="document.id", primary_key=True)
    galaxy_id: UUID = Field(foreign_key="galaxy.id", primary_key=True)
    relevance_score: float = Field(default=0.0)
    perspective_summary: Optional[str] = Field(default=None)
    hit_frequency: int = Field(default=0)
    last_aligned_at: datetime = Field(default_factory=datetime.utcnow)
    document: "Document" = Relationship(back_populates="galaxy_links")
    galaxy: "Galaxy" = Relationship(back_populates="document_links")

# --- 🚀 [V3.0] 文档与逻辑脊梁 (100% 物理还原) ---

class Document(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    filename: str = Field(index=True)
    file_path: str
    file_hash: Optional[str] = Field(index=True)
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    error_message: Optional[str] = Field(default=None)
    
    is_toc_locked: bool = Field(default=False)
    is_scanned: bool = Field(default=False)
    page_offset: int = Field(default=0)
    processed_pages: int = Field(default=0)
    total_pages: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    workspace_id: Optional[UUID] = Field(default=None, foreign_key="workspace.id")
    folder_id: Optional[UUID] = Field(default=None, foreign_key="folder.id")
    nexus_atlas: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSONB))
    
    workspace: Optional[Workspace] = Relationship(back_populates="documents")
    folder: Optional[Folder] = Relationship(back_populates="documents")
    tags: List[Tag] = Relationship(back_populates="documents", link_model=DocumentTagLink)
    galaxy_links: List[DocumentGalaxyLink] = Relationship(back_populates="document")
    
    toc_items: List["TocItem"] = Relationship(back_populates="document", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    chunks: List["Chunk"] = Relationship(back_populates="document", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    metrics: List["ProcessingMetric"] = Relationship(back_populates="document")

class TocItem(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str
    page: int
    level: int
    confidence: float = Field(default=1.0)
    
    summary: Optional[str] = Field(default=None)
    keywords: Optional[List[str]] = Field(default=None, sa_column=Column(JSON))
    embedding: Optional[List[float]] = Field(sa_column=Column(Vector(settings.EMBEDDING_DIMENSION)))
    keyword_embedding: Optional[List[float]] = Field(sa_column=Column(Vector(settings.EMBEDDING_DIMENSION)))
    
    physical_start: int = Field(default=0)
    physical_end: int = Field(default=0)
    offset_verified: bool = Field(default=False)
    is_synthetic: bool = Field(default=False)
    
    document_id: UUID = Field(foreign_key="document.id")
    parent_id: Optional[UUID] = Field(default=None, foreign_key="tocitem.id")
    
    document: Optional["Document"] = Relationship(back_populates="toc_items")
    parent: Optional["TocItem"] = Relationship(back_populates="children", sa_relationship_kwargs={"remote_side": "TocItem.id"})
    children: List["TocItem"] = Relationship(back_populates="parent")

class Chunk(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    content: str
    page_number: int
    breadcrumb: Optional[str] = Field(default=None)
    embedding: List[float] = Field(sa_column=Column(Vector(settings.EMBEDDING_DIMENSION)))

    document_id: UUID = Field(foreign_key="document.id", ondelete="CASCADE")
    toc_item_id: Optional[UUID] = Field(default=None, foreign_key="tocitem.id", ondelete="SET NULL")
    level: int = Field(default=1)

    confidence_score: float = Field(default=1.0) # 🚀 保持物理一致

    logic_tags: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSONB))
    metadata_json: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    causality_links: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSONB))
    
    document: Document = Relationship(back_populates="chunks")
    revisions: List["ChunkRevision"] = Relationship(back_populates="chunk")

    # 🕸️ [V7.0] 逻辑织网 - 出边关系
    outgoing_relationships: List["ChunkRelationship"] = Relationship(
        back_populates="source_chunk",
        sa_relationship_kwargs={"foreign_keys": "ChunkRelationship.source_chunk_id"}
    )
    # 🕸️ [V7.0] 逻辑织网 - 入边关系
    incoming_relationships: List["ChunkRelationship"] = Relationship(
        back_populates="target_chunk",
        sa_relationship_kwargs={"foreign_keys": "ChunkRelationship.target_chunk_id"}
    )


# --- 🕸️ [V7.0] 逻辑织网协议 (Judgment Breeds Connectivity) ---

class RelationshipType(str, Enum):
    """
    Chunk 关系谓词枚举 - 不可变的关系 Schema

    每一条"边"都必须喊出它的逻辑意义，拒绝廉价的联想。
    """
    CAUSALITY = "causality"        # A 导致 B，或 A 是 B 的前提
    CONTRADICTION = "contradiction" # A 与 B 存在逻辑冲突（触发法庭记录）
    SUPPORT = "support"            # A 为 B 提供物理层面的证据支撑
    EVOLUTION = "evolution"        # B 是 A 的修正版本（跨文档知识更迭）
    COMPLEMENT = "complement"      # A 和 B 描述同一实体的不同维度


class ChunkRelationship(SQLModel, table=True):
    """
    Chunk 关系表 - 逻辑织网的物理载体

    设计哲学:
      - 关联不是数据录入，是审判后的质证结论
      - 只有经过联邦法庭审判的 Chunk 才配拥有连接键
      - 每条关系都代表系统对事实关联的郑重承诺

    使用场景:
      - Moderator 裁决后，GraphWeaver 自动缝合关系
      - Distributor 传唤时，顺着关系键进行"逻辑爬行"寻址
    """
    __table_args__ = {"extend_existing": True}

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # 关系两端
    source_chunk_id: UUID = Field(foreign_key="chunk.id", index=True)
    target_chunk_id: UUID = Field(foreign_key="chunk.id", index=True)

    # 关系谓词（核心逻辑）
    rel_type: RelationshipType = Field(index=True)

    # 关系强度 (0.0-1.0) - 由 Moderator 裁决时评估
    strength: float = Field(default=1.0)

    # 关系描述（人类可读，由 LLM 生成）
    description: Optional[str] = None

    # 证据溯源 - 指向触发此关系的 Court Verdict
    verdict_id: Optional[UUID] = Field(default=None, index=True)

    # 元数据
    created_by: str = Field(default="GraphWeaver")  # 创建者（Agent 名称）
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    source_chunk: Chunk = Relationship(
        back_populates="outgoing_relationships",
        sa_relationship_kwargs={"foreign_keys": "[ChunkRelationship.source_chunk_id]"}
    )
    target_chunk: Chunk = Relationship(
        back_populates="incoming_relationships",
        sa_relationship_kwargs={"foreign_keys": "[ChunkRelationship.target_chunk_id]"}
    )


# --- 🚀 [V6.0] 知识代谢账本 (作为新表存在，承载代谢状态) ---

class ChunkRevision(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    chunk_id: UUID = Field(foreign_key="chunk.id", ondelete="CASCADE")
    
    # 修改详情
    old_content: Optional[str] = None
    new_content: str
    change_reason: str
    contributor_agent: str
    
    # 🚀 代谢状态：挪到这里，不再污染 Chunk 物理表
    veracity_score: float = 1.0
    is_deprecated: bool = False
    
    revision_number: int = 1
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    chunk: Chunk = Relationship(back_populates="revisions")

# --- ⚖️ [V8.0] 司法档案库 (Court Verdict Archive) ---

class CourtVerdict(SQLModel, table=True):
    """
    ⚖️ 联邦判决书：记录每一次联邦法庭审判的完整全景。
    职责：为 Refinery 提供推理迹语料，为用户提供审计溯源。
    """
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    query: str = Field(index=True)
    
    # 🏛️ 核心产出
    final_answer: str
    reasoning_thought: Optional[str] = Field(default=None, sa_column=Column(JSONB)) # 存储完整的思考链
    verdict_decision: str = Field(default="ACCEPTED") # ACCEPTED | CONFLICT | PARTIAL
    
    # 📡 证据溯源
    cited_galaxies: List[str] = Field(default_factory=list, sa_column=Column(JSONB))
    confidence_score: float = Field(default=0.0)
    
    # 📈 元数据
    duration_ms: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # 可选：关联具体的文档链接（用于深度跳转）
    # metadata_json: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))

class ProcessingMetric(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(foreign_key="document.id", index=True)
    stage: str = Field(index=True)
    duration_ms: int
    status: str = Field(default="success")
    error_info: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    document: Document = Relationship(back_populates="metrics")

class EventLog(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    event_type: str = Field(index=True)
    payload: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSONB))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user: User = Relationship(back_populates="event_logs")
