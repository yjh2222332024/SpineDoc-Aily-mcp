"""
Retrieval Module - Multi-document retrieval with conflict resolution
====================================================================

Front-end pipeline (still active, called by LogicCourt):
- QueryRouter: Routes queries to relevant document sources
- EvidenceCollector: Collects evidence from multiple sources in parallel

Graph-based pipeline (active, replaces old RetrievalCoordinator):
- LogicCourtCoordinator (graph/coordinator.py): Main graph engine
- Planner → Harvester → Auditor → Synthesizer → Evolution
"""

__all__ = []