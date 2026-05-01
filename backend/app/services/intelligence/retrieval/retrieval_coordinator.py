"""
RetrievalCoordinator - Unified entry for multi-document retrieval
================================================================
Responsibility: Orchestrate QueryRouter, EvidenceCollector, and ConflictResolver
to complete multi-document retrieval with conflict resolution.
"""

import asyncio
import time
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings
from .query_state import QueryState
from .query_router import QueryRouter
from .evidence_collector import EvidenceCollector
from .conflict_resolver import ConflictResolver
from backend.app.services.knowledge.graph_weaver import GraphWeaver


class RetrievalCoordinator:
    """
    RetrievalCoordinator

    Responsibility:
    Orchestrate the complete process: Query Routing -> Evidence Collection -> Conflict Resolution
    """

    def __init__(self):
        self.router = QueryRouter()
        self.collector = EvidenceCollector()
        self.resolver = ConflictResolver()
        self.graph_weaver = GraphWeaver()
        self.source_results = []

    async def retrieve(
        self,
        query: str,
        limit_per_source: int = 3,
        enable_online: bool = False
    ) -> Dict[str, Any]:
        """
        Complete retrieval process with conflict resolution
        """
        start_time = time.time()

        # LLM Configuration Check
        llm_error = await self._probe_llm()
        if llm_error:
            print(f"[RetrievalCoordinator] LLM unavailable: {llm_error}")
            return {
                "final_answer": f"LLM service unavailable: {llm_error}",
                "confidence": 0.0,
                "cited_sources": [],
                "reasoning": "LLM configuration validation failed"
            }

        print("\n" + "=" * 60)
        print(f"RetrievalCoordinator started: {query[:settings.CONTEXT_COMMIT_QUERY_PREFIX]}...")
        if enable_online:
            print("[Mode] Online data source activated, knowledge base may be updated")
        print("=" * 60)

        # --- Phase 1: Query Routing ---
        print("\n[Phase 1] Routing query to sources...")
        state = QueryState()
        state["retrieved_sources"] = await self.router.route_query(
            query,
            limit_per_source=limit_per_source
        )

        if not state["retrieved_sources"]:
            print("No relevant documents found, using fallback strategy...")
            return {
                "final_answer": "No relevant documents found, cannot generate result.",
                "confidence": 0.0,
                "cited_sources": [],
                "reasoning": "QueryRouter did not find any relevant documents"
            }

        # --- Phase 2: Evidence Collection ---
        print("\n[Phase 2] Collecting evidence...")
        source_results = await self.collector.collect_evidence(
            state["retrieved_sources"],
            query,
            enable_online=enable_online
        )
        state["source_results"] = source_results
        self.source_results = source_results

        # --- Phase 3: Conflict Resolution ---
        print("\n[Phase 3] Resolving conflicts...")
        final_result = await self.resolver.resolve(
            source_results, query
        )
        state["final_result"] = final_result

        # --- Phase 4: Graph Integration ---
        print("\n[Phase 4] Graph integration...")
        try:
            relationships = self._extract_relationships_from_result(final_result)
            if relationships:
                import uuid
                result_id = str(uuid.uuid4())
                final_result["id"] = result_id

                created = self.graph_weaver.weave_from_result(final_result)
                print(f"   ↳ Integrated {len(created)} relationships")
            else:
                print("   ↳ No relationships declared, skipping integration")
        except Exception as e:
            print(f"   Integration failed: {e}")

        # --- Phase 5: Answer Building ---
        print("\n[Phase 5] Building answer...")
        from .answer_builder import AnswerBuilder
        builder = AnswerBuilder()

        final_answer = await builder.build_answer(
            query=query,
            final_result=final_result,
            source_results=source_results,
            temperature=0.7
        )

        final_result["final_answer"] = final_answer
        final_result["source_results"] = source_results

        # Inject phase metadata for card transparency
        final_result["_phase_meta"] = {
            "phase1_routed": True,
            "phase1_source_count": len(state["retrieved_sources"]),
            "phase2_chunk_count": sum(len(sr.get("evidence_chunks", [])) for sr in source_results),
            "phase3_conflict_count": final_result.get("_phase_meta", {}).get("conflict_count", 0),
            "phase4_relationship_count": final_result.get("id") and 1 or 0,
            "phase5_completed": True,
            "confidence": final_result.get("confidence", 0.0),
            "color": final_result.get("color", "YELLOW"),
        }
        # Clean up private field before returning
        final_result.pop("_phase_meta", None)

        print("Answer building completed")

        print("\n" + "=" * 60)
        print("RetrievalCoordinator finished")
        print("=" * 60)

        return final_result

    async def _probe_llm(self) -> Optional[str]:
        """LLM Availability Probe"""
        from backend.app.core.config import settings
        from openai import AsyncOpenAI

        if not settings.LLM_API_KEY:
            return "LLM_API_KEY not configured"
        if not settings.LLM_BASE_URL:
            return "LLM_BASE_URL not configured"

        try:
            client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

            response = await asyncio.wait_for(
                client.chat.completions.create(
                    model=settings.LLM_MODEL_NAME,
                    messages=[{"role": "user", "content": "OK"}],
                    max_tokens=5
                ),
                timeout=10.0
            )
            if not response or not response.choices:
                return "LLM probe returned empty response"
            return None
        except asyncio.TimeoutError:
            return "LLM probe timeout (10s)"
        except Exception as e:
            return f"LLM probe failed: {e}"

    async def retrieve_single(self, query: str, doc_id: str) -> Dict[str, Any]:
        """Single document retrieval synthesis"""
        print(f"\nRetrievalCoordinator single: {query[:settings.CONTEXT_COMMIT_QUERY_PREFIX]}... @ {doc_id[:settings.CONTEXT_COMMIT_DOC_ID_PREFIX]}")

        from backend.app.services.intelligence.interrogator.graph import interrogator_graph

        initial_state = {
            "query": query,
            "doc_id": doc_id,
            "toc": [],
            "sub_queries": [],
            "fingerprint_pool": [],
            "selected_ids": [],
            "pro_evidence": [],
            "citation_ids": [],
            "is_sufficient": False,
            "final_answer": ""
        }

        result = await interrogator_graph.ainvoke(initial_state)
        return {
            "final_answer": result.get("final_answer", ""),
            "confidence": 1.0 if result.get("is_sufficient") else 0.5,
            "cited_sources": [],
            "reasoning": "Single document synthesis, no conflict resolution"
        }

    def _extract_relationships_from_result(self, final_result: Dict) -> List[Dict]:
        """Extract proposed_relationships from final_result"""
        relationships = []

        resolved_conflicts = final_result.get("resolved_conflicts", [])
        for conflict in resolved_conflicts:
            proposed = conflict.get("proposed_relationships", [])
            relationships.extend(proposed)

        delta = final_result.get("knowledge_update", {})
        if isinstance(delta, dict):
            proposed = delta.get("proposed_relationships", [])
            relationships.extend(proposed)

        return relationships