import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from backend.app.core.config import settings
from backend.app.services.intelligence.retrieval.utils.conflict_detector import ConflictDetector
from backend.app.services.intelligence.retrieval.utils.update_scanner import UpdateScanner

logger = logging.getLogger(__name__)


class ConflictResolver:
    """
    ConflictResolver: Orchestrates multi-source evidence conflict detection and resolution.
    """
    def __init__(self, detector=None, scanner=None):
        self.detector = detector or ConflictDetector()
        self.scanner = scanner or UpdateScanner()
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL
        )

    async def resolve(self, source_results: List[Dict], query: str) -> Dict[str, Any]:
        """
        Main orchestration flow for conflict resolution.
        """
        print(f"[ConflictResolver] Orchestrating resolution for {len(source_results)} sources...")

        # 1. Detection Phase
        conflicts = await self.detector.detect(source_results, query)
        print(f"[ConflictResolver] Detected {len(conflicts)} conflicts")

        # 2. Resolution Phase
        resolved_conflicts = []
        for conflict in conflicts:
            resolution = await self._resolve_single_conflict(conflict, query, source_results)
            conflict["resolution"] = resolution
            resolved_conflicts.append(conflict)

        # 3. Verdict Phase
        final_result = await self._generate_result(source_results, conflicts, query)
        final_result["resolved_conflicts"] = resolved_conflicts

        # 4. Knowledge Update Phase
        final_result["knowledge_update"] = self.scanner.scan_for_updates(
            source_results, resolved_conflicts, query
        )

        # 5. Phase metadata (conflict resolution summary)
        final_result["_phase_meta"] = {
            "conflict_count": len(conflicts),
            "resolved_conflict_count": len(resolved_conflicts),
            "has_conflict": len(conflicts) > 0,
            "has_knowledge_delta": final_result["knowledge_update"].get("has_delta", False),
        }

        return final_result

    async def _resolve_single_conflict(self, conflict: Dict, query: str, source_results: List[Dict]) -> Dict:
        """
        Resolve a single conflict using LLM reasoning.
        Present both sides, ask the LLM to adjudicate based on evidence quality.
        """
        packages = conflict.get("packages", [])
        if len(packages) < 2:
            return {"decision": "no_conflict", "reasoning": "Insufficient evidence for adjudication."}

        # Build evidence context for each side — with objective confidence scores injected
        evidence_text = ""
        for i, pkg in enumerate(packages):
            chunk_id = pkg.get("chunk_id", "")
            claim = pkg.get("claim", "")
            source_name = pkg.get("source_name", "Unknown")

            # Find full evidence chunk for richer context + objective metrics
            full_content = ""
            confidence = None
            published_date = None
            color = None
            for sr in source_results:
                for ec in sr.get("evidence_chunks", []):
                    if ec.get("id") == chunk_id:
                        full_content = ec.get("content", claim)
                        confidence = ec.get("confidence")
                        published_date = ec.get("published_date")
                        color = ec.get("color")
                        break

            conf_str = f"{confidence:.3f}" if confidence is not None else "?"
            date_str = published_date or "未知"
            color_str = color or "?"

            evidence_text += f"""--- 来源 {i+1}: {source_name} ---
主张: {claim}
完整内容: {full_content[:500]}
📊 客观指标 → 置信度: {conf_str} | 颜色: {color_str} | 发布日期: {date_str}

"""

        prompt = f"""You are a rigorous evidence adjudicator. Two sources contradict each other on the query: "{query}"

【Conflict Description】
{conflict.get('description', 'Unknown conflict')}

【Evidence from Both Sides】
{evidence_text}

【Severity】
{conflict.get('severity', 'MINOR')}

Your task:
1. Analyze which source provides more authoritative, complete, and logically consistent evidence
2. Consider: source quality, recency, completeness of reasoning, specificity of claims
3. Determine the resolution:
   - "accept_first": First source is more authoritative
   - "accept_second": Second source is more authoritative
   - "merge_both": Both sources are correct in different contexts — provide a merged conclusion
   - "undetermined": Cannot determine authority, present both

4. Provide clear reasoning for your decision

Output strict JSON:
{{
    "decision": "accept_first" | "accept_second" | "merge_both" | "undetermined",
    "reasoning": "Why this decision was made (100-200 words)",
    "merged_conclusion": "Only if merge_both: the synthesized conclusion"
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            result = json.loads(response.choices[0].message.content)
            return result
        except Exception as e:
            logger.error(f"Conflict adjudication failed: {e}")
            return {"decision": "undetermined", "reasoning": f"Adjudication failed: {e}"}

    async def _generate_result(self, sources: List[Dict], conflicts: List[Dict], query: str) -> Dict[str, Any]:
        """
        Synthesize final answer based on all evidence and resolutions.
        Uses LLM to build a comprehensive answer that accounts for conflicts and resolutions.
        """
        # Build unified evidence context
        evidence_parts = []
        for i, src in enumerate(sources):
            chunks_text = ""
            for c in src.get("evidence_chunks", []):
                chunks_text += f"  [P{c.get('page_number', '?')}] {c.get('content', '')[:300]}\n"
            evidence_parts.append(f"""【Source {i+1}: {src.get('source_name', 'Unknown')}】
{chunks_text}""")

        evidence_context = "\n".join(evidence_parts)

        # Build conflict resolution summary
        conflict_summary = ""
        for c in conflicts:
            resolution = c.get("resolution", {})
            decision = resolution.get("decision", "undetermined")
            reasoning = resolution.get("reasoning", "No reasoning provided")

            conflict_summary += f"""
冲突: {c.get('description', 'Unknown')}
裁决: {decision}
理由: {reasoning}
"""

        prompt = f"""You are a chief analyst synthesizing evidence from multiple documents to answer a query.

【Query】
{query}

【Evidence from {len(sources)} Sources】
{evidence_context}

【Conflicts Detected and Resolved】
{conflict_summary if conflicts else "No conflicts detected."}

【Resolution Guide】
{"Here are the adjudicated resolutions — follow them when forming your answer." if conflicts else ""}

Your task:
1. Synthesize a comprehensive, accurate answer to the query
2. Where conflicts exist, follow the adjudicated resolution
3. Cite specific evidence sources (source names)
4. Assign a confidence score (0.0-1.0) based on:
   - Evidence quality and completeness
   - Number and severity of unresolved conflicts
   - Consistency across sources
5. Assign a confidence color:
   - GREEN: >= 0.8 (strong evidence, consistent)
   - YELLOW: 0.5-0.8 (moderate evidence, some conflicts)
   - RED: < 0.5 (weak evidence, major contradictions)

Output strict JSON:
{{
    "final_answer": "The synthesized answer (300-500 words, in Chinese)",
    "confidence": 0.0-1.0,
    "color": "GREEN" | "YELLOW" | "RED",
    "cited_sources": ["Source name 1", "Source name 2"],
    "reasoning": "Brief summary of how the answer was derived (100 words)"
}}
"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            result = json.loads(response.choices[0].message.content)
            result.setdefault("color", "YELLOW")
            result.setdefault("cited_sources", [s.get("source_name", "") for s in sources])
            result.setdefault("reasoning", "Evidence synthesized with conflict resolution.")
            return result
        except Exception as e:
            logger.error(f"Result synthesis failed: {e}")
            return {
                "final_answer": f"Synthesis failed: {e}",
                "confidence": 0.0,
                "color": "RED",
                "cited_sources": [s.get("source_name", "") for s in sources],
                "reasoning": "Failed during synthesis."
            }
