"""
Schema definitions for Retrieval Graph
======================================
Graph Execution State TypedDict 定义
"""
from typing import TypedDict, List, Dict, Any, Annotated, Optional
import operator


from pydantic import BaseModel, Field

class EvidenceSchema(BaseModel):
    """ [V270.0] 统一证据片 Schema (Pydantic 强制校验) """
    id: str = Field(..., description="证据唯一标识")
    content: str = Field(..., description="原始文本或 PRUNED")
    claims: List[str] = Field(default_factory=list, description="原子主张列表")
    origin: str = Field(..., description="来源标识: LOCAL_GALAXY | INTERNET_WITNESS | A-MEMORY")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    color: str = Field(default="YELLOW")
    stability: float = Field(default=0.5)
    doc_id: Optional[str] = None
    breadcrumb: Optional[str] = ""
    page_number: Optional[int] = 0
    is_sovereign: bool = Field(default=False, description="主权标识: True 本地主权 | False 联网证人")
    source_name: str = Field(default="Unknown", description="证据来源名称")

class GraphExecutionState(TypedDict):
    """
    SpineDoc Multi-Agent Retrieval Graph State (V2.0)
    ==========================================
    Single source of truth for the multi-agent graph.
    """
    # --- Input Domain ---
    query: str                       # Original user query
    doc_id: str                      # Target document ID ("all" for multi-doc)
    sub_queries: List[str]           # Split sub-tasks by Planner

    # --- Evidence Domain ---
    evidence_pool: List[Dict[str, Any]]
    L3_archive: List[Dict[str, Any]]

    # --- Weight Domain ---
    claim_weights: Dict[str, float]

    # --- Decision Domain ---
    agreed_claims: List[str]
    conflicts: List[Dict[str, Any]]
    verdict: Dict[str, Any]

    # --- Target Domain ---
    target_galaxy_ids: List[str]

    # --- Control Domain ---
    next_step: str
    iteration: int
    final_answer: str

    # --- Subpoena Domain ---
    investigation_order: str
    re_harvest_count: int

    # --- Interaction Domain ---
    phase_log: List[Dict[str, Any]]


# 向后兼容别名
CourtState = GraphExecutionState

__all__ = ["CourtState", "GraphExecutionState"]