from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, JSON
from sqlalchemy.dialects.postgresql import JSONB # 🚀 保持 JSONB 兼容性
from app.core.config import settings 

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

# --- 🚀 [V1.0] 后台监控与性能 ---

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
