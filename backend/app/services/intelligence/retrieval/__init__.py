"""
Retrieval Module - Multi-document retrieval with conflict resolution
====================================================================
Business semantics naming (no metaphor):
- RetrievalCoordinator: Main entry, orchestrates the complete retrieval process
- QueryRouter: Routes queries to relevant document sources
- EvidenceCollector: Collects evidence from multiple sources in parallel
- ConflictResolver: Detects and resolves conflicts between evidence
- AnswerBuilder: Builds human-readable answers from results
"""

from .retrieval_coordinator import RetrievalCoordinator

__all__ = ["RetrievalCoordinator"]