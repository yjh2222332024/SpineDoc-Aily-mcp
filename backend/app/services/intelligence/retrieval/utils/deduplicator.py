"""
SemanticDeduplicator - Evidence Deduplication
=============================================
Two-phase dedup: ID-based (fast) + Semantic similarity (accurate).
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class SemanticDeduplicator:
    """Two-phase evidence deduplication."""

    def __init__(self, embedding_service=None, similarity_threshold: float = 0.92):
        self.similarity_threshold = similarity_threshold
        self._embedding_service = embedding_service

    async def deduplicate(self, evidence_pool: List[Dict]) -> List[Dict]:
        if not evidence_pool:
            return []

        # Phase 1: ID-based dedup (O(n))
        seen_ids = set()
        id_deduped = []
        for e in evidence_pool:
            eid = e.get("id")
            if eid and eid not in seen_ids:
                seen_ids.add(eid)
                id_deduped.append(e)

        if len(id_deduped) <= 1:
            return id_deduped

        # Phase 2: Semantic dedup (if embedding service available)
        if not self._embedding_service:
            return id_deduped

        try:
            texts = [self._extract_text(e) for e in id_deduped]
            vectors = await self._embedding_service.get_embeddings_batch(texts)
            keep_indices = self._find_unique_indices(vectors, self.similarity_threshold)
            return [id_deduped[i] for i in keep_indices]
        except Exception as e:
            logger.warning(f"Semantic dedup failed, falling back to ID dedup: {e}")
            return id_deduped

    def _extract_text(self, evidence: Dict) -> str:
        claims = evidence.get("claims", [])
        if claims:
            return " ".join(claims)[:500]
        return evidence.get("content", "")[:500]

    def _find_unique_indices(self, vectors: List, threshold: float) -> List[int]:
        import numpy as np
        keep = []
        vecs = np.array(vectors, dtype=np.float32)
        norms = np.linalg.norm(vecs, axis=1)
        for i in range(len(vecs)):
            is_dup = False
            for j in keep:
                sim = float(np.dot(vecs[i], vecs[j]) / (norms[i] * norms[j] + 1e-10))
                if sim > threshold:
                    is_dup = True
                    break
            if not is_dup:
                keep.append(i)
        return keep
