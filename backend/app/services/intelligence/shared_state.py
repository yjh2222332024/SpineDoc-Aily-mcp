"""
Shared State Space — Multi-Agent Shared State Hub
==================================================
Defines the unified AgentState TypedDict and StateBroker for
cross-agent state sharing in SpineDoc.
"""

import asyncio
import copy
from typing import List, Dict, Any, Optional, TypedDict


class EvidenceChunk(TypedDict, total=False):
    """Basic unit for conflict analysis."""
    id: str
    content: str
    page_number: int
    breadcrumb: str
    logic_tags: List[str]


class SourceResult(TypedDict, total=False):
    """All evidence from a single source document."""
    doc_id: str
    source_id: str
    source_name: str
    evidence_chunks: List[EvidenceChunk]
    sub_queries: List[str]
    error: Optional[str]


class ConflictItem(TypedDict, total=False):
    """Logical contradiction that needs resolution."""
    description: str
    packages: List[Dict[str, Any]]
    severity: str
    resolution: Optional[Dict[str, Any]]


class AgentState(TypedDict, total=False):
    """
    Unified state shared across all retrieval agents.
    Covers single-doc interrogation, multi-doc retrieval, and knowledge graph phases.
    """
    # --- Query Context ---
    query: str
    doc_id: str
    sub_queries: List[str]

    # --- Source Data (multi-doc) ---
    retrieved_sources: List[Dict[str, str]]
    source_results: List[SourceResult]

    # --- Evidence (single-doc) ---
    fingerprint_pool: List[Dict]
    selected_ids: List[str]
    evidence_chunks: List[EvidenceChunk]

    # --- Conflict State ---
    conflicts_found: List[ConflictItem]

    # --- Knowledge Graph ---
    relationships: List[Dict[str, Any]]

    # --- Confidence ---
    confidence: float
    color: str

    # --- Result ---
    final_answer: str
    result_metadata: Dict[str, Any]


class StateBroker:
    """
    Thread-safe shared state hub for multi-agent coordination.

    Agents publish partial updates and read the full state.
    Uses asyncio.Lock for async safety.
    """

    def __init__(self, query: str = ""):
        self._state: Dict[str, Any] = {
            "query": query,
            "sub_queries": [],
            "doc_id": "",
            "retrieved_sources": [],
            "source_results": [],
            "fingerprint_pool": [],
            "selected_ids": [],
            "evidence_chunks": [],
            "conflicts_found": [],
            "relationships": [],
            "confidence": 0.0,
            "color": "YELLOW",
            "final_answer": "",
            "result_metadata": {},
        }
        self._lock = asyncio.Lock()

    async def publish(self, agent_id: str, updates: Dict[str, Any]) -> None:
        """An agent publishes partial state updates."""
        async with self._lock:
            for key, value in updates.items():
                if key in self._state:
                    self._state[key] = value
            self._state.setdefault("result_metadata", {})["last_agent"] = agent_id

    async def subscribe(self) -> Dict[str, Any]:
        """Read current state (returns a copy)."""
        async with self._lock:
            return copy.deepcopy(self._state)

    async def snapshot(self) -> Dict[str, Any]:
        """Get a frozen snapshot of current state."""
        return await self.subscribe()

    async def get(self, key: str) -> Any:
        """Read a single field."""
        async with self._lock:
            return copy.deepcopy(self._state.get(key))

    async def clear(self) -> None:
        """Reset state for a new query."""
        async with self._lock:
            for key in self._state:
                if isinstance(self._state[key], list):
                    self._state[key] = []
                elif isinstance(self._state[key], dict):
                    self._state[key] = {}
                elif isinstance(self._state[key], str):
                    self._state[key] = ""
                elif isinstance(self._state[key], (int, float)):
                    self._state[key] = 0.0
