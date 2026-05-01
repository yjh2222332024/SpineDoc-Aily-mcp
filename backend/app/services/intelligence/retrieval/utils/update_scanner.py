import logging
from typing import List, Dict, Any
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class UpdateScanner:
    """
    UpdateScanner: Identifies which chunks need updating based on resolution and online results.
    Responsibility: Knowledge Delta Analysis (Pure Logic).
    """
    def __init__(self):
        pass

    def scan_for_updates(
        self, 
        source_results: List[Dict], 
        resolved_conflicts: List[Dict], 
        query: str
    ) -> Dict[str, Any]:
        """
        Scan all results to identify knowledge deltas.
        """
        updated_chunks = []
        
        # 1. Process Resolved Conflicts
        updated_chunks.extend(self._scan_conflicts(source_results, resolved_conflicts))
        
        # 2. Process Online Supplements
        updated_chunks.extend(self._scan_online_results(source_results))

        return {
            "has_delta": len(updated_chunks) > 0,
            "updated_chunks": updated_chunks,
            "commit_message": self._generate_commit_message(query, updated_chunks, resolved_conflicts)
        }

    def _scan_conflicts(self, source_results: List[Dict], resolved_conflicts: List[Dict]) -> List[Dict]:
        updates = []
        for resolved in resolved_conflicts:
            if resolved.get("resolution", {}).get("decision") in ("undetermined", "无法裁决"):
                continue
                
            for pkg in resolved.get("packages", []):
                doc_prefix = pkg.get("doc_id", "")[:8]
                for result in source_results:
                    if result.get("doc_id", "").startswith(doc_prefix):
                        for chunk in result.get("evidence_chunks", []):
                            updates.append(self._build_update_record(chunk, result, resolved))
        return updates

    def _scan_online_results(self, source_results: List[Dict]) -> List[Dict]:
        updates = []
        for result in source_results:
            if not result.get("is_online"):
                continue
            for chunk in result.get("evidence_chunks", []):
                if chunk.get("color") in ["GREEN", "BLUE"]:
                    updates.append(self._build_create_record(chunk))
        return updates

    def _build_update_record(self, chunk: Dict, result: Dict, resolved: Dict) -> Dict:
        return {
            "chunk_id": chunk.get("id"),
            "source_name": result.get("source_name"),
            "change_type": "update",
            "reason": f"Conflict resolution: {resolved.get('description', 'Unknown')[:settings.CONTEXT_EVIDENCE_REASON_PREFIX]}",
            "old_content": chunk.get("content", "")[:settings.CONTEXT_CHUNK_PREVIEW_CONTENT],
            "color": chunk.get("color", "YELLOW")
        }

    def _build_create_record(self, chunk: Dict) -> Dict:
        return {
            "chunk_id": chunk.get("id"),
            "source_name": "Online Retriever",
            "change_type": "create",
            "reason": f"Online evidence supplement: {chunk.get('source_title', 'Unknown')[:settings.CONTEXT_EVIDENCE_REASON_PREFIX]}",
            "new_content": chunk.get("content", "")[:settings.CONTEXT_CHUNK_PREVIEW_CONTENT],
            "color": chunk.get("color", "YELLOW"),
            "metadata": {
                "source_url": chunk.get("source_url"),
                "published_date": chunk.get("published_date")
            }
        }

    def _generate_commit_message(self, query: str, updates: List, conflicts: List) -> str:
        q_prefix = query[:settings.CONTEXT_COMMIT_QUERY_PREFIX]
        if conflicts:
            return f"Resolved \"{q_prefix}\" - {len(conflicts)} conflicts"
        if updates:
            return f"Updated \"{q_prefix}\" - {len(updates)} evidence chunks"
        return ""
