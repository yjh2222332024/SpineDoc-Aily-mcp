"""
TermMapManager - Term mapping table manager
==========================================
Responsibility: Read storage/term_map.json, provide cluster query service.
This is the "map" for the retrieval system to locate relevant source clusters.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Set
from backend.app.core.config import settings


class TermMapManager:
    """
    Term mapping table manager

    Responsibilities:
    1. Load Term Map (source cluster mapping table)
    2. Match related clusters based on query keywords
    3. Return all source information under the cluster
    """

    def __init__(self, map_path: Optional[str] = None):
        if map_path is None:
            map_path = str(Path(settings.STORAGE_ROOT) / "term_map.json")
        self.map_path = Path(map_path)
        self.term_map: Dict[str, Dict] = {}
        self._load_map()

    def _load_map(self):
        """Load Term Map"""
        if self.map_path.exists():
            try:
                with open(self.map_path, "r", encoding="utf-8") as f:
                    self.term_map = json.load(f)
                print(f"🗺️ [TermMapManager] Loaded map: {len(self.term_map)} clusters")
            except Exception as e:
                print(f"⚠️ [TermMapManager] Load error: {e}")
                self.term_map = {}
        else:
            print(f"⚠️ [TermMapManager] Map not found: {self.map_path}")

    def find_clusters_by_query(self, query: str) -> List[str]:
        """
        Match related clusters based on query keywords

        Strategy:
        1. Extract keywords from query (simple tokenization)
        2. Match anchor_keywords of clusters
        3. Return matched cluster_id list
        """
        if not self.term_map:
            return []

        keywords = set(re.split(r'[\s,_/-]+', query.lower()))
        keywords = {kw for kw in keywords if len(kw) > 1}

        matched_clusters = []
        for cluster_id, data in self.term_map.items():
            anchor_keywords = data.get("anchor_keywords", [])
            for anchor in anchor_keywords:
                anchor_lower = anchor.lower()
                if anchor_lower in keywords or any(kw in anchor_lower for kw in keywords):
                    matched_clusters.append(cluster_id)
                    break

        if not matched_clusters:
            return list(self.term_map.keys())

        return matched_clusters

    def get_cluster_sources(self, cluster_id: str) -> List[Dict]:
        """Get all sources under specified cluster"""
        if cluster_id in self.term_map:
            return self.term_map[cluster_id].get("sources", [])
        return []

    def get_all_source_ids(self, cluster_ids: List[str]) -> Set[str]:
        """Get all source ID sets under multiple clusters"""
        source_ids = set()
        for cluster_id in cluster_ids:
            sources = self.get_cluster_sources(cluster_id)
            for source in sources:
                source_ids.add(source["id"])
        return source_ids

    def get_source_info(self, source_id: str) -> Optional[Dict]:
        """Find source info by source_id"""
        for cluster_id, data in self.term_map.items():
            for source in data.get("sources", []):
                if source["id"] == source_id:
                    return {
                        "id": source["id"],
                        "name": source["name"],
                        "cluster_id": cluster_id
                    }
        return None