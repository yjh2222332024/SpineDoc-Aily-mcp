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
    🕸️ [V7.0] 逻辑织网协议 - 增加 [V53.5] 代谢奖惩扩展
    设计哲学：模拟神经突触的动态可塑性（Synaptic Plasticity）。
    """
    __table_args__ = {"extend_existing": True}

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    source_chunk_id: UUID = Field(foreign_key="chunk.id", index=True)
    target_chunk_id: UUID = Field(foreign_key="chunk.id", index=True)

    rel_type: RelationshipType = Field(index=True)

    # 🚀 [V53.5] 代谢权重系统 (Metabolic Weight System)

    # 【辩护：最大熵原则】 
    # 依据：Jaynes (1957) 信息论最大熵原理 & BAKE (Han et al. 2025) 贝叶斯先验。
    # 设定 0.5 理由：在 [0,1] 概率区间内，0.5 代表系统的最大不确定性状态（Prior Uncertainty）。
    # 既不假设关联成立，也不假设其不成立，等待“多巴胺”或“内啡肽”信号进行后验修正。
    strength: float = Field(default=0.5) 
    
    # 【辩护：奖励预测误差 RPE】
    # 依据：Schultz (1997) & Berry (Cell 2015) 的 Dopamine RPE 模型。
    # 设定 0.0 理由：多巴胺记录的是“预期之外的增量”。初始状态下无预测误差，
    # 仅当布朗运动碰撞出“远端节点”且法庭判定有效时，该值才会激增，驱动灵感产生。
    dopamine_reward: float = Field(default=0.0) 
    
    # 【辩护：阿片类固化机制】
    # 依据：Trezza (PNAS 2007) & Hebbian Learning (1949) "Wire together, Fire together"。
    # 设定 0.0 理由：内啡肽代表系统的“镇静与稳定”力量。稳定性是随时间（重复激活）累积的，
    # 初始状态为 0（Tabula Rasa），随验证次数增加而单调上升。
    endorphin_stability: float = Field(default=0.0) 

    description: Optional[str] = None
    verdict_id: Optional[UUID] = Field(default=None, index=True)

    created_by: str = Field(default="GraphWeaver")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # 【辩护：突触稳态缩放】
    # 依据：Turrigiano (2012) & Physiological Reviews (2013) 的 Synaptic Scaling 模型。
    # 作用：记录时间锚点，用于计算公式 Δw = -λ * w 中的衰减系数 λ，实现“选择性遗忘”。
    last_activated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    source_chunk: Chunk = Relationship(
        back_populates="outgoing_relationships",
        sa_relationship_kwargs={"foreign_keys": "[ChunkRelationship.source_chunk_id]"}
    )
    target_chunk: Chunk = Relationship(
        back_populates="incoming_relationships",
        sa_relationship_kwargs={"foreign_keys": "[ChunkRelationship.target_chunk_id]"}
    )


# --- 🧬 [V53.5] 代谢进化核心载体 (The Metabolic Forge) ---

class MetabolicTrace(SQLModel, table=True):
    """
    🌀 梦境轨迹：记录布朗运动产生的思维漂移路径。
    依据：Mastering Diverse Domains through World Models (Nature 2023) 中的 Latent Imagination 轨迹。
    """
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    seed_chunk_id: UUID = Field(foreign_key="chunk.id", index=True)
    path_nodes: List[UUID] = Field(default_factory=list, sa_column=Column(JSONB)) 
    
    drift_distance: float = Field(default=0.0) # 向量空间漂移距离
    innovation_score: float = Field(default=0.0) # 潜在逻辑张力
    
    is_merged: bool = Field(default=False) 
    created_at: datetime = Field(default_factory=datetime.utcnow)


class LogicTension(SQLModel, table=True):
    """
    ⚡ 逻辑张力审计：量化灵感与真理的冲突程度。
    依据：SpineDoc 原创量化公式 LT = Novelty * Validity。
    支撑论文中的 [LT] 指标，作为多巴胺奖励的计算输入。
    """
    __table_args__ = {"extend_existing": True}
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    trace_id: Optional[UUID] = Field(default=None, foreign_key="metabolictrace.id")
    verdict_id: UUID = Field(foreign_key="courtverdict.id")
    
    novelty_score: float = Field(default=0.0) 
    validity_score: float = Field(default=0.0) 
    tension_value: float = Field(default=0.0) 
    
    analysis_text: str 
    created_at: datetime = Field(default_factory=datetime.utcnow)


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
