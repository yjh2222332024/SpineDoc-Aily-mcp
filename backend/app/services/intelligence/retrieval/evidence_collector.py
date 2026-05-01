"""
EvidenceCollector - Collects evidence from multiple document sources
====================================================================
Responsibility: Parallel execution of single-document retrieval, returning evidence chunks
for conflict resolution by the ConflictResolver.
"""

import asyncio
import json
from typing import List, Dict
from uuid import UUID

from backend.app.services.rag.aily_harvester import aily_harvester
from backend.app.services.feishu.bitable_ledger import bitable_ledger
from openai import AsyncOpenAI
from backend.app.core.config import settings
from .online_retriever import OnlineRetriever
from .color_confidence import ColorConfidenceCalculator, ConfidenceColor


class EvidenceCollector:
    """
    EvidenceCollector - Collects evidence from multiple sources

    Responsibilities:
    1. Receive retrieved document list
    2. Execute parallel retrieval for each document (via Aily cloud)
    3. Return evidence chunks
    """

    def __init__(self):
        # 🚀 [V60.0] Dynamic routing: adapted for Doubao 2.0
        self.client = AsyncOpenAI(
            api_key=settings.REAL_LLM_KEY,
            base_url=settings.LLM_BASE_URL
        )
        self.online_retriever = OnlineRetriever()
        self.color_calc = ColorConfidenceCalculator()

    async def collect_evidence(
        self,
        retrieved_sources: List[Dict[str, str]],
        query: str,
        enable_online: bool = False
    ) -> List[Dict]:
        """
        Parallel execution of single-document retrieval, collecting all evidence chunks (including online)

        Args:
            retrieved_sources: Retrieved source list
            query: Original query
            enable_online: Whether to activate online retriever

        Returns:
            source_results: [{'doc_id': '...', 'source_id': '...', 'source_name': '...', 'evidence_chunks': [...], 'sub_queries': [...]}]
        """
        print(f"📡 [EvidenceCollector] Starting collection from {len(retrieved_sources)} sources...")
        if enable_online:
            print("🌐 [EvidenceCollector] Online retriever activated")

        # 1. Decompose query (for online retrieval)
        sub_queries = await self._decompose_query(query)

        # 2. Parallel: local collection + online collection (optional)
        total_source_count = len(retrieved_sources) + (1 if online_result_data else 0)
        local_tasks = [
            self._collect_from_source(doc, query, sub_queries, total_source_count)
            for doc in retrieved_sources
        ]

        # Online collection (only when enable_online=True)
        online_result_data = None
        if enable_online:
            print("🌐 [EvidenceCollector] Calling online retriever...")
            try:
                online_result = await self.online_retriever.retrieve(sub_queries)

                # Check if online result is valid
                if online_result.get("error") or not online_result.get("evidence_chunks"):
                    print(f"⚠️ [EvidenceCollector] Online retriever returned empty result or error")
                    raise Exception("Online retrieval returned no valid results")

                online_result_data = online_result
                print("✅ [EvidenceCollector] Online retrieval successful")
            except Exception as e:
                print(f"⚠️ [EvidenceCollector] Online retrieval failed: {e}")
                print(f"💤 [EvidenceCollector] Online service unavailable, sleeping {settings.ZHIPU_FALLBACK_SLEEP_SECONDS}s then degrading to offline mode...")
                await asyncio.sleep(settings.ZHIPU_FALLBACK_SLEEP_SECONDS)
                print("🔌 [EvidenceCollector] Degraded to offline mode, continuing local collection...")

        # Gather local tasks (all are coroutines)
        results = await asyncio.gather(*local_tasks, return_exceptions=True)

        # Separate local and online results
        source_results = []
        for i, result in enumerate(results):
            doc_info = retrieved_sources[i]
            if isinstance(result, Exception):
                print(f"⚠️ [EvidenceCollector] Source {doc_info['doc_id'][:8]} collection failed: {result}")
                source_results.append({
                    "doc_id": doc_info["doc_id"],
                    "source_id": doc_info["source_id"],
                    "source_name": doc_info["source_name"],
                    "evidence_chunks": [],
                    "sub_queries": sub_queries,
                    "error": str(result)
                })
            else:
                source_results.append(result)

        # Add online result if available
        if online_result_data:
            source_results.append(online_result_data)

        print(f"✅ [EvidenceCollector] Collection complete: {len(source_results)} source results")
        return source_results

    async def _collect_from_source(
        self,
        doc: Dict[str, str],
        query: str,
        sub_queries: List[str],
        total_source_count: int = 1
    ) -> Dict:
        """
        Single source evidence collection flow (cloud version):
        1. AilyHarvester: Cloud retrieve chunks
        2. Examiner: Select most relevant chunks
        3. Return evidence chunks
        """
        doc_id = doc["doc_id"]
        source_id = doc["source_id"]
        source_name = doc["source_name"]

        print(f"  📝 [EvidenceCollector] Cloud collection: {source_name} → {doc_id[:8]}...")

        # --- Step 1: Aily cloud harvest ---
        all_chunks = []
        seen_ids = set()

        for sub_query in sub_queries:
            chunks = await aily_harvester.harvest(sub_query, doc_record_id=doc_id, limit=10)
            for chunk in chunks:
                if chunk['id'] not in seen_ids:
                    all_chunks.append(chunk)
                    seen_ids.add(chunk['id'])

        print(f"    ↳ Retrieved {len(all_chunks)} candidate chunks")

        # --- Step 2: Examiner select chunks ---
        selected_chunks = await self._examine_chunks(query, all_chunks, doc_id)
        print(f"    ↳ Examiner locked {len(selected_chunks)} core chunks")

        # --- Step 3: Return evidence (Aily/Bitable already contains content) ---
        evidence_chunks = []
        for c in selected_chunks:
            color, confidence = self.color_calc.calculate(
                c,
                independent_sources=total_source_count,
                has_conflict=False
            )
            c["color"] = color.value
            c["confidence"] = confidence
            c["type"] = "CLOUD_BITABLE"
            evidence_chunks.append(c)

        return {
            "doc_id": doc_id,
            "source_id": source_id,
            "source_name": source_name,
            "evidence_chunks": evidence_chunks,
            "sub_queries": sub_queries
        }

    async def _decompose_query(self, query: str) -> List[str]:
        """Query decomposition"""
        prompt = f"""You are a top forensic audit scout. Your task is to decompose a complex audit query into 3 specific sub-tasks.

【Main Query】：{query}

Requirements:
1. Sub-tasks must be specific, searchable short phrases
2. Sub-tasks should be logically complementary
3. Strictly output JSON object format: {{"sub_queries": ["q1", "q2", "q3"]}}
"""
        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            data = json.loads(response.choices[0].message.content)
            return data.get("sub_queries", [query])
        except:
            return [query]

    async def _examine_chunks(
        self,
        query: str,
        chunks: List[Dict],
        doc_id: str
    ) -> List[Dict]:
        """
        Examiner: Select chunks under source context and pre-detect "logical collision" points.
        """
        # Load TOC
        toc = await self._load_toc(doc_id)

        # Construct fingerprint pool with source context
        fingerprint_pool = []
        for c in chunks:
            fingerprint_pool.append({
                "id": c["id"],
                "p": c["page_number"],
                "path": c["breadcrumb"],
                "tags": c.get("logic_tags", [])[:settings.CONTEXT_LOGIC_TAGS_LIMIT],
                "source": c.get("source_name", "Unknown Source")
            })

        toc_limit = settings.COURT_CONTEXT_TOC_LIMIT

        prompt = f"""You are a top forensic examiner. Please select evidence under source context and pre-detect potential "logical collisions".

【Audit Target Source Context】:
Each evidence chunk carries source identification. Note:
- Different sources may hold different positions (e.g., "Legal source" tends toward risk control, "Technical source" tends toward implementation)
- When multiple sources provide similar evidence, note the subtle differences between them

【Target Document TOC】：
{json.dumps(toc[:toc_limit], ensure_ascii=False)}

【Candidate Evidence Fingerprint Pool】：
{json.dumps(fingerprint_pool, ensure_ascii=False)}

【Original Audit Query】：
{query}

Your tasks:
1. Select 3-5 most representative Chunk IDs.
2. Execute "collision pre-detection":
   - Identify which selected Chunks may conflict with evidence from other sources
   - Identify which Chunks, though from different pages, have highly consistent logical claims (cross-validation)
3. Provide your "examination reasoning".

Output format (strict JSON）：
{{
    "selections": [
        {{
            "id": "uuid",
            "reason": "Why select it? What is its representativeness in its source?",
            "potential_collisions": ["Other Chunk IDs or keywords that may conflict with it"]
        }}
    ],
    "pre_audit_note": "Overall evaluation of this document's evidence quality"
}}
"""
        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            data = json.loads(response.choices[0].message.content)
            selections = data.get("selections", [])
            selected_ids = {s["id"] for s in selections}

            final_chunks = []
            for c in chunks:
                if c["id"] in selected_ids:
                    s_meta = next((s for s in selections if s["id"] == c["id"]), {})
                    c["pre_audit_reason"] = s_meta.get("reason")
                    c["potential_collisions"] = s_meta.get("potential_collisions", [])
                    final_chunks.append(c)

            # Fallback: if LLM didn't select, take top RRF scored
            if not final_chunks and chunks:
                print(f"  ⚠️ [Examiner] LLM failed to lock valid evidence, using RRF fallback")
                sorted_chunks = sorted(chunks, key=lambda x: x.get('rrf_score', 0), reverse=True)
                return sorted_chunks[:settings.CONTEXT_FALLBACK_CHUNKS]

            return final_chunks
        except Exception as e:
            print(f"  ⚠️ [Examiner] Exception: {e}, using RRF fallback")
            sorted_chunks = sorted(chunks, key=lambda x: x.get('rrf_score', 0), reverse=True)
            return sorted_chunks[:settings.CONTEXT_FALLBACK_CHUNKS]

    async def _load_toc(self, doc_id: str) -> List[Dict]:
        """Load document TOC from Bitable"""
        try:
            items = await bitable_ledger.search_chunks(query="", doc_record_id=doc_id, limit=100)
            tocs = []
            seen_titles = set()
            for it in items:
                title = it.get("breadcrumb")
                if title and title not in seen_titles:
                    tocs.append({"title": title, "page": it.get("page_number", 0), "level": 1})
                    seen_titles.add(title)
            return tocs
        except Exception as e:
            print(f"⚠️ [EvidenceCollector] Failed to load cloud TOC: {e}")
            return []