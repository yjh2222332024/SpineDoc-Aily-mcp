"""
CourtState Adapters — Bridge between SpineEngine and graph nodes.
"""

from typing import Dict, Any
from .schema import CourtState


def create_initial_court_state(query: str) -> CourtState:
    """
    Create a bare CourtState for a fresh LogicCourt run.
    The graph starts from PLAN, and HarvesterNode handles all evidence collection.
    """
    return CourtState(
        query=query,
        sub_queries=[],
        evidence_pool=[],
        L3_archive=[],
        claim_weights={},
        agreed_claims=[],
        conflicts=[],
        verdict=None,
        target_galaxy_ids=[],
        investigation_order=None,
        re_harvest_count=0,
        next_step="PLAN",
        iteration=0,
        final_answer=None,
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
    }
