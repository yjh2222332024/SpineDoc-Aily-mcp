"""
AnswerBuilder - Builds human-readable answers from evidence and resolutions
============================================================================
Responsibility: Receive adjudicator's resolution and raw evidence, produce readable "human" answers.
Mode: Automatically switch between "Mentor" and "Chief Registrar" personas based on evidence count.

Architecture Philosophy:
    Chief Justice must maintain 0.1 low temperature to prevent hallucinations.
    Diplomat needs 0.7 soul temperature for "semantic association and stitching".
    Abstract questions (like "zero-based introduction") require creative integration from the model.
"""

import json
import logging
from typing import List, Dict, Any
from backend.app.infra.llm_client import get_llm_client
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class AnswerBuilder:
    """
    AnswerBuilder - Generates readable answers from retrieval results

    Responsibilities:
    1. Receive resolver's final result and raw evidence
    2. Automatically switch personas based on evidence count
    3. Produce highly readable "human" answers
    """

    def __init__(self):
        self.client = get_llm_client()

    async def build_answer(
        self,
        query: str,
        final_result: Dict,
        source_results: List[Dict],
        temperature: float = 0.6
    ) -> str:
        """
        Core synthesis logic: connect logical islands, smooth subjective question anxiety.

        Args:
            query: Original query
            final_result: Resolver's final result
            source_results: Source results list
            temperature: Soul temperature (0.6-0.7 for creative integration)

        Returns:
            Integrated answer string
        """
        print(f"🖋️  [AnswerBuilder] Building answer in mode {'SINGLE' if len(source_results)==1 else 'MULTI'}...")

        # 1. Prepare synthesis context
        context = self._prepare_context(source_results)
        reasoning = final_result.get("reasoning", "No conflicts or consensus reached.")

        # 2. Determine persona and instructions
        is_single = len(source_results) == 1
        system_prompt = self._get_persona_prompt(is_single)

        # 3. Construct request
        user_msg = f"""【Original Query】：{query}

【Resolution Conclusion】：
{reasoning}

【Physical Evidence Base】：
{json.dumps(context, ensure_ascii=False, indent=2)}

Please based on the above materials, write a well-structured, easy-to-understand answer for the user.
"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.REAL_LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AnswerBuilder crashed: {e}")
            return final_result.get("final_answer", "AnswerBuilder temporarily unavailable, please refer to raw retrieval result.")

    def _prepare_context(self, results: List[Dict]) -> List[Dict]:
        """
        Extract evidence essence with coordinate feel

        Args:
            results: Source results list

        Returns:
            Simplified context list
        """
        simplified_context = []
        for result in results:
            chunks = []
            for c in result.get("evidence_chunks", []):
                chunks.append({
                    "p": c.get("page_number"),
                    "path": c.get("breadcrumb"),
                    "content": c.get("content")
                })
            simplified_context.append({
                "source": result.get("source_name", "Unknown Source"),
                "evidence": chunks
            })
        return simplified_context

    def _get_persona_prompt(self, is_single: bool) -> str:
        """
        Switch persona based on evidence count

        Args:
            is_single: Whether in single-document mode

        Returns:
            System prompt string
        """
        if is_single:
            return """You are a learned technical mentor (Mentor).
Your responsibility is to integrate枯燥的文档片段 into a 'learning guide'.

Core principles:
1. **Path-oriented**: Use page numbers and chapter paths to outline clear steps or concept levels for the user.
2. **Logical bonding**: Use your general knowledge to connect scattered evidence blocks, explain their intrinsic connections.
3. **Source annotation**: Must annotate physical coordinates after each key conclusion, format like: (Pxx | Chapter Name).
4. **Honesty principle**: If evidence truly doesn't mention something, you can give direction based on common sense, but must declare 'inferred from common sense' or 'recommend consulting more chapters'.

Response style:
- Use Markdown format
- Organize content by steps and levels
- Like a patient mentor guiding the user step by step
- Give command examples for key operations"""
        else:
            return """You are a rigorous chief recorder (Chief Registrar).
Your responsibility is to summarize multi-source federal judgments, give authoritative 'industry overview'.

Core principles:
1. **Balance sense**: Clearly distinguish what is consensus and what is conflict.
2. **Source attribution**: When stating different viewpoints, clearly indicate their source (e.g., 'In Source_Technical, there is a tendency to...').
3. **Objective summary**: Based on ConflictResolver's resolution, give a final comprehensive judgment.
4. **Structured**: Use Markdown titles, lists, and bold to ensure extremely high readability.

Response style:
- Use Markdown format
- Summarize consensus first, then elaborate differences
- Like an authoritative recorder, give final comprehensive judgment"""