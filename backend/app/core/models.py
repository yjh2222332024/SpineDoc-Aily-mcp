from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, JSON
from sqlalchemy.dialects.postgresql import JSONB # 🚀 [V48.5] 引入 JSONB
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

# --- 🚀 [V5.0] 知识星系核心架构 (Operation Galaxy Breath) ---

class Galaxy(SQLModel, table=True):
    """
    🏛️ 知识星系 (Macro-Cluster)
    职责：定义宏观语义边界，作为引力中心。
    """
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: str                    # LLM 视角下的星系定义 (用于调度员意图匹配)
    
    # 星系语义重心：由所属文档簇蒸馏而出的向量
    centroid_embedding: List[float] = Field(
        sa_column=Column(Vector(settings.EMBEDDING_DIMENSION))
    )
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    document_links: List["DocumentGalaxyLink"] = Relationship(back_populates="galaxy")

class DocumentGalaxyLink(SQLModel, table=True):
    """
    🔗 引力链接 (The Breathing Link)
    职责：管理 N:N 映射，记录文档在不同星系引力下的“坍缩状态”。
    """
    __table_args__ = {"extend_existing": True}
    document_id: UUID = Field(foreign_key="document.id", primary_key=True)
    galaxy_id: UUID = Field(foreign_key="galaxy.id", primary_key=True)
    
    relevance_score: float = Field(default=0.0) # 关联强度 (0.0 - 1.0)
    perspective_summary: Optional[str] = Field(default=None) # 星系视角摘要
    
    hit_frequency: int = Field(default=0)
    last_aligned_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    document: "Document" = Relationship(back_populates="galaxy_links")
    galaxy: "Galaxy" = Relationship(back_populates="document_links")

# --- 🚀 [V3.0] 文档与逻辑脊梁 (ISR) ---

class Document(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    filename: str = Field(index=True)
    file_path: str
    file_hash: Optional[str] = Field(index=True)
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    
    is_scanned: bool = Field(default=False)
    page_offset: int = Field(default=0)
    total_pages: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    workspace_id: Optional[UUID] = Field(default=None, foreign_key="workspace.id")
    folder_id: Optional[UUID] = Field(default=None, foreign_key="folder.id")

    # 🚀 [V35.0] Nexus 全景画像
    nexus_atlas: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSONB))
    
    # Relationships
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
    
    summary: Optional[str] = Field(default=None)
    keywords: Optional[List[str]] = Field(default=None, sa_column=Column(JSONB))
    embedding: Optional[List[float]] = Field(sa_column=Column(Vector(settings.EMBEDDING_DIMENSION)))
    
    physical_start: int = Field(default=0)
    physical_end: int = Field(default=0)
    is_synthetic: bool = Field(default=False) # 🚀 [V3.5] 涌现标记
    
    document_id: UUID = Field(foreign_key="document.id")
    parent_id: Optional[UUID] = Field(default=None, foreign_key="tocitem.id")
    
    document: Optional["Document"] = Relationship(back_populates="toc_items")
    parent: Optional["TocItem"] = Relationship(back_populates="children", sa_relationship_kwargs={"remote_side": "TocItem.id"})
    children: List["TocItem"] = Relationship(back_populates="parent")

# --- 🚀 [V6.0] Chunk 进化与代谢账本 (LLM Wiki Genome) ---

class Chunk(SQLModel, table=True):
    """
    🧬 文本分块表 (V6.0 Wiki 活性版)
    职责：作为知识检索与质证的最小全息单元。
    """
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    content: str
    page_number: int
    breadcrumb: Optional[str] = Field(default=None)
    embedding: List[float] = Field(sa_column=Column(Vector(settings.EMBEDDING_DIMENSION)))

    # --- 物理/逻辑锚点 ---
    document_id: UUID = Field(foreign_key="document.id", ondelete="CASCADE")
    toc_item_id: Optional[UUID] = Field(default=None, foreign_key="tocitem.id", ondelete="SET NULL")
    level: int = Field(default=1) # 🚀 必须保留，否则入库崩溃

    # --- 🚀 活性基因 (Holographic Genome) ---
    veracity_score: float = Field(default=1.0)   # 真实性得分 (实时同步)
    confidence_score: float = Field(default=1.0) # 🚀 兼容旧版：逻辑置信度
    is_deprecated: bool = Field(default=False)    # 是否被废弃 (代谢开关)
    
    # 星系引力钉选：手动或 Agent 标记的固定引力
    galaxy_weights: Optional[Dict[str, float]] = Field(default_factory=dict, sa_column=Column(JSONB))

    logic_tags: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSONB))
    metadata_json: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSONB))
    causality_links: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSONB)) # 🚀 必须保留
    
    # Relationships
    document: Document = Relationship(back_populates="chunks")
    revisions: List["ChunkRevision"] = Relationship(back_populates="chunk")

class ChunkRevision(SQLModel, table=True):
    """
    📖 知识代谢账本 (Metabolism Ledger)
    职责：剥离高频更新的审计逻辑与历史快照。
    """
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    chunk_id: UUID = Field(foreign_key="chunk.id", ondelete="CASCADE")
    
    # --- 修改细节 ---
    old_content: Optional[str] = None
    new_content: str
    change_reason: str                  # 修改动机
    contributor_agent: str              # [WitnessNode, GrandJustice, Human]
    
    veracity_delta: float = 0.0         # 置信度变化量
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
