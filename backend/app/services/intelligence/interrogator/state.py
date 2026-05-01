from typing import List, Dict, Any, TypedDict, Optional

class InterrogatorState(TypedDict):
    """
    Single-document interrogation state contract.
    Domain: Intelligence / Interrogator (backend service layer)
    Responsibility: Track the full lifecycle from intent decomposition to evidence selection.
    """
    # --- Core Input ---
    query: str                          # Original query
    doc_id: str                         # Target document ID
    toc: List[Dict]                     # Target document's logical spine (TOC)

    # --- Decomposition Phase ---
    sub_queries: List[str]              # Decomposed sub-query tasks

    # --- Harvest Phase ---
    fingerprint_pool: List[Dict]        # Full harvest fingerprint pool (ID, Path, Tags)
    selected_ids: List[str]             # Selector's final evidence IDs

    # --- Synthesis Phase ---
    pro_evidence: List[Dict]            # Full-text evidence content
    citation_ids: List[str]             # Referenced chunk ID list

    # --- State Control ---
    is_sufficient: bool                 # Whether evidence is sufficient
    final_answer: str                   # Final synthesized answer
