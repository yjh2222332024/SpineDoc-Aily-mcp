"""
QueryState - Multi-document retrieval state contract
=====================================================
Defines the state structure for multi-document retrieval.
Core: Evidence chunks are the basic unit for conflict analysis.
"""

from typing import List, Dict, Any, TypedDict, Optional


class EvidenceChunk(TypedDict):
    """
    Evidence chunk: basic unit for conflict analysis.
    """
    id: str
    content: str
    page_number: int
    breadcrumb: str
    logic_tags: List[str]


class SourceResult(TypedDict):
    """
    Source result: all evidence from a single source document.
    """
    doc_id: str
    source_id: str
    source_name: str
    evidence_chunks: List[EvidenceChunk]
    sub_queries: List[str]
    error: Optional[str]


class ConflictItem(TypedDict):
    """
    Conflict point: logical contradiction that needs resolution.
    """
    description: str
    packages: List[Dict[str, Any]]
    severity: str  # "CRITICAL" | "MINOR"
    resolution: Optional[Dict[str, Any]]


class QueryState(TypedDict):
    """
    Query State Contract

    Responsibilities: Manage the full lifecycle from routing to final result.

    Pipeline:
    1. Routing (route_query)  → retrieved_sources
    2. Collection (collect_evidence) → source_results
    3. Resolution (resolve_conflicts) → conflicts_found + final_result
    """
    # --- Core Input ---
    query: str

    # --- Phase 1: Routing ---
    retrieved_sources: List[Dict[str, str]]  # [{'doc_id': '...', 'source_id': '...', 'source_name': '...'}]

    # --- Phase 2: Collection ---
    source_results: List[SourceResult]

    # --- Phase 3: Resolution ---
    conflicts_found: List[ConflictItem]
    final_result: Optional[Dict[str, Any]]

    # --- State Control ---
    is_complete: bool