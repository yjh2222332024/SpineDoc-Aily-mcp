"""
Schema definitions for Retrieval Graph
======================================
Graph Execution State TypedDict 定义
"""
from typing import TypedDict, List, Dict, Any, Annotated
import operator


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
    evidence_pool: Annotated[List[Dict[str, Any]], operator.add]
    L3_archive: Annotated[List[Dict[str, Any]], operator.add]

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