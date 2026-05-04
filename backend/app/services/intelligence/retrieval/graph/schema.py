from typing import TypedDict, List, Dict, Any, Annotated, Optional
import operator

class CourtState(TypedDict):
    """
    SpineDoc Federated Logic Court State (V1.2)
    ==========================================
    Single source of truth for the multi-agent graph.
    """
    # --- Input Domain ---
    query: str                       # Original user query
    sub_queries: List[str]           # Split sub-tasks by Planner

    # --- Evidence Domain ---
    # Hot & Warm Cache (L1/L2)
    evidence_pool: Annotated[List[Dict[str, Any]], operator.add]
    # Cold Storage (L3 Archive) - Pruned or de-weighted evidence
    L3_archive: Annotated[List[Dict[str, Any]], operator.add]

    # --- Weight Domain ---
    # Dynamic weighting of claims: {evidence_id: weight_multiplier}
    claim_weights: Dict[str, float]

    # --- Decision Domain ---
    agreed_claims: List[str]         # Facts validated by multiple agents
    conflicts: List[Dict[str, Any]]  # Detected logical contradictions
    verdict: Optional[Dict[str, Any]] # 🚀 SOTA: The Internal Truth & Assistant Response

    # --- Target Domain ---
    target_galaxy_ids: List[str]      # 🚀 physical IDs for Bitable backfill

    # --- Control Domain ---
    next_step: str                   # State machine control: PLAN, HARVEST, AUDIT, SYNTHESIZE, END
    iteration: int                   # Loop counter to prevent infinite reasoning
    final_answer: Optional[str]      # The end result to be delivered to the user

    # --- Subpoena Domain (V1.2) ---
    investigation_order: Optional[str]  # Supplementary search directive from AUDIT → HARVEST
    re_harvest_count: int               # How many times we've looped back for more evidence
