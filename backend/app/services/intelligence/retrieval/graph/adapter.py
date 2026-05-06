"""
CourtState Adapters — Bridge between SpineEngine and graph nodes.
"""

from typing import Dict, Any
from .schema import CourtState


def create_initial_court_state(query: str, doc_id: str = "all") -> CourtState:
    """
    Create a bare CourtState for a fresh LogicCourt run.
    For single-doc queries, skip PLAN (no sub-query splitting needed).
    """
    is_single_doc = bool(doc_id and doc_id != "all")
    return CourtState(
        query=query,
        doc_id=doc_id,
        sub_queries=[query] if is_single_doc else [],
        evidence_pool=[],
        L3_archive=[],
        claim_weights={},
        agreed_claims=[],
        conflicts=[],
        verdict=None,
        target_galaxy_ids=[],
        investigation_order=None,
        re_harvest_count=0,
        next_step="HARVEST" if is_single_doc else "PLAN",
        iteration=0,
        final_answer=None,
        phase_log=[],   #  [V230.0] 阶段时间线
    )


def adapt_court_state_to_hybrid_output(state: CourtState) -> Dict[str, Any]:
    """
    Convert final CourtState into the dict format expected by
    SpineEngine.hybrid_ask() callers.
    """
    # Final answer
    verdict = state.get("verdict") or {}
    final_answer = (
        verdict.get("assistant_answer")
        or state.get("final_answer")
        or "Unable to generate answer."
    )

    # Confidence: average of claim_weights
    weights = state.get("claim_weights", {})
    if weights:
        confidence = sum(weights.values()) / len(weights)
    else:
        confidence = 0.0

    # Color: derived from average confidence
    if confidence >= 0.8:
        color = "GREEN"
    elif confidence >= 0.5:
        color = "YELLOW"
    else:
        color = "RED"

    # Cited sources: deduplicate source_name from evidence_pool
    pool = state.get("evidence_pool", [])
    cited = list(dict.fromkeys(e.get("source_name", "Unknown") for e in pool if e.get("source_name")))

    # Reasoning: brief summary
    conflicts = state.get("conflicts", [])
    if conflicts:
        reasoning = f"Detected {len(conflicts)} conflicts during adjudication."
    else:
        reasoning = "No conflicts detected during adjudication."

    return {
        "final_answer": final_answer,
        "confidence": round(confidence, 3),
        "color": color,
        "cited_sources": cited,
        "reasoning": reasoning,
        "phase_log": state.get("phase_log", []),     #  [V230.0] 阶段时间线
    }
