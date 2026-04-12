from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, JSON
from app.core.config import settings # 🆕 移到顶部

class ProcessingStatus(str, Enum):
    """文档处理状态枚举"""
    PENDING = "pending"
    PARTIAL = "partial"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# 多对多关联表：文档-标签
class DocumentTagLink(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    document_id: UUID = Field(foreign_key="document.id", primary_key=True)
    tag_id: UUID = Field(foreign_key="tag.id", primary_key=True)

class User(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    """用户表"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    workspaces: List["Workspace"] = Relationship(back_populates="owner")
    event_logs: List["EventLog"] = Relationship(back_populates="user")

class Workspace(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    """工作空间表"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    owner_id: UUID = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    owner: User = Relationship(back_populates="workspaces")
    documents: List["Document"] = Relationship(back_populates="workspace", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    folders: List["Folder"] = Relationship(back_populates="workspace", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class Folder(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    """文件夹表"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str
    parent_id: Optional[UUID] = Field(default=None, foreign_key="folder.id")
    workspace_id: UUID = Field(foreign_key="workspace.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    workspace: Workspace = Relationship(back_populates="folders")
    parent: Optional["Folder"] = Relationship(back_populates="children", sa_relationship_kwargs={"remote_side": "Folder.id"})
    children: List["Folder"] = Relationship(back_populates="parent")
    documents: List["Document"] = Relationship(back_populates="folder")

class Tag(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    """标签表"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True)
    color: str = "#808080"
    workspace_id: UUID = Field(foreign_key="workspace.id")
    
    documents: List["Document"] = Relationship(back_populates="tags", link_model=DocumentTagLink)

class Document(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    """文档表"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    filename: str = Field(index=True)
    file_path: str
    file_hash: Optional[str] = Field(index=True)
    status: ProcessingStatus = Field(default=ProcessingStatus.PENDING)
    error_message: Optional[str] = Field(default=None)
    is_toc_locked: bool = Field(default=False)
    is_scanned: bool = Field(default=False) # 🆕 显式标记扫描件
    page_offset: int = Field(default=0)     # 🆕 逻辑/物理页码偏移
    processed_pages: int = Field(default=0) # 已处理页数
    total_pages: int = Field(default=0)     # 总页数
    created_at: datetime = Field(default_factory=datetime.utcnow)

    updated_at: datetime = Field(default_factory=datetime.utcnow)

    workspace_id: Optional[UUID] = Field(default=None, foreign_key="workspace.id")
    folder_id: Optional[UUID] = Field(default=None, foreign_key="folder.id")

    # Relationships
    workspace: Optional[Workspace] = Relationship(back_populates="documents")
    folder: Optional[Folder] = Relationship(back_populates="documents")
    tags: List[Tag] = Relationship(back_populates="documents", link_model=DocumentTagLink)
    
    # 🚀 [V35.0] Nexus 全景画像：存储文档在全局逻辑网中的位置、摘要及关键指标
    nexus_atlas: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    
    toc_items: List["TocItem"] = Relationship(back_populates="document", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    chunks: List["Chunk"] = Relationship(back_populates="document", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    metrics: List["ProcessingMetric"] = Relationship(back_populates="document", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class TocItem(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    """
    目录项表 (V6.5 语义锚点版)
    职责：不仅是目录，更是正文灵魂的载体。
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str
    page: int # 逻辑页码 (书上印的)
    level: int
    confidence: float = Field(default=1.0)
    
    # 🆕 语义增强：正文灵魂反哺
    summary: Optional[str] = Field(default=None) # LLM 生成的章节综述
    keywords: Optional[List[str]] = Field(
        default=None, 
        sa_column=Column(JSON)
    ) # 🆕 KeyBERT 提炼的领域关键词
    
    embedding: Optional[List[float]] = Field(
        default=None, 
        sa_column=Column(Vector(settings.EMBEDDING_DIMENSION))
    ) # 标题向量
    
    keyword_embedding: Optional[List[float]] = Field(
        default=None, 
        sa_column=Column(Vector(settings.EMBEDDING_DIMENSION))
    ) # 🆕 核心：关键词聚合向量 (检索磁石)

    # 🆕 物理对齐：物理疆域地图
    physical_start: int = Field(default=0) # 🆕 映射后的起始物理页
    physical_end: int = Field(default=0)   # 🆕 映射后的结束物理页
    offset_verified: bool = Field(default=False) # 🆕 是否经过视觉锚定校验
    
    # 邻接表设计：支持树形目录
    parent_id: Optional[UUID] = Field(default=None, foreign_key="tocitem.id")
    document_id: UUID = Field(foreign_key="document.id")
    
    document: Optional["Document"] = Relationship(back_populates="toc_items")
    # 自关联关系，用于 SQLAlchemy 的层级预加载
    parent: Optional["TocItem"] = Relationship(
        back_populates="children", 
        sa_relationship_kwargs={"remote_side": "TocItem.id"}
    )
    children: List["TocItem"] = Relationship(back_populates="parent")

class Chunk(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    """文本分块表"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    content: str
    page_number: int
    breadcrumb: Optional[str] = Field(default=None)
    embedding: List[float] = Field(sa_column=Column(Vector(settings.EMBEDDING_DIMENSION)))

    # 架构师加固：建立与目录项的直接物理关联
    toc_item_id: Optional[UUID] = Field(default=None, foreign_key="tocitem.id", ondelete="SET NULL")
    document_id: UUID = Field(foreign_key="document.id", ondelete="CASCADE")
    level: int = Field(default=1) # 🆕 增加层级属性

    # 🆕 纯图 PDF 支持：元数据 JSON 字段
    metadata_json: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    # 包含：physical_page, ocr_confidence, is_scanned, ocr_engine, has_table, has_formula 等

    # 🚀 [V35.0] NexusNode 核心扩展
    logic_tags: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    causality_links: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON)) 
    # 存储：{"implies": ["node_id_1"], "conflict_with": ["node_id_2"], "reasoning": "..."}
    
    confidence_score: float = Field(default=1.0) # 由多模型投票或证据强度决定

    document: Optional[Document] = Relationship(back_populates="chunks")

# --- Analytics Models ---

class EventLog(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    """用户行为日志表 (Analytics)"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    event_type: str = Field(index=True) # e.g., "document_view", "search"
    # 使用 SQLAlchemy 的 JSON 类型存储动态负载
    payload: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="event_logs")

class ProcessingMetric(SQLModel, table=True):
    __table_args__ = {"extend_existing": True}
    """后台处理性能指标表 (Audit)"""
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    document_id: UUID = Field(foreign_key="document.id", index=True)
    stage: str = Field(index=True) # e.g., "ocr", "parsing", "vectorizing"
    duration_ms: int
    status: str = Field(default="success") # success, failed
    error_info: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    document: Document = Relationship(back_populates="metrics")