
"""
📜 SpineDoc Audit Contract - 审计结论契约
=========================================
职责：定义后端引擎输出到交互层的标准数据模型。
架构：属于 Interaction Layer，作为跨模块通信的唯一合法数据协议。
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum

class VerdictColor(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    BLUE = "BLUE"

class ConflictResolution(BaseModel):
    description: str
    decision: str
    reasoning: str

class PhaseMetadata(BaseModel):
    phase1_source_count: int = 0
    phase2_chunk_count: int = 0
    phase3_conflict_count: int = 0
    phase4_relationship_count: int = 0
    confidence: float = 0.0
    color: VerdictColor = VerdictColor.YELLOW

class AuditVerdict(BaseModel):
    """
    这是后端引擎必须交付给交互层的‘终极数据报文’。
    """
    id: str = Field(..., description="审计任务或逻辑块的唯一标识")
    query: str = Field(..., description="原始审计质询")
    text: str = Field(..., description="审计结论正文")
    confidence: float = Field(0.0, description="置信度评分 (0-1)")
    color: VerdictColor = Field(VerdictColor.YELLOW, description="风险等级颜色")
    
    cited_sources: List[str] = Field(default_factory=list, description="引用的物理页码或来源列表")
    
    # 过程元数据（用于在卡片上展示时间线）
    phase_meta: Optional[PhaseMetadata] = None
    
    # 冲突详情
    resolved_conflicts: List[ConflictResolution] = Field(default_factory=list)
    
    # 扩展字段
    extra_data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True
