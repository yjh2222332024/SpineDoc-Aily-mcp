import json
import logging
from typing import List, Dict, Any, Optional
from backend.app.infra.llm_client import get_llm_client
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class ConflictDetector:
    """
    ConflictDetector: Specializes in identifying contradictions between evidence chunks.
    Responsibility: Evidence Analysis + LLM Communication.
    """
    def __init__(self, client=None):
        self.client = client or get_llm_client()

    async def detect(self, source_results: List[Dict], query: str) -> List[Dict]:
        """
        Detect logical conflicts between evidence chunks using LLM.
        """
        if len(source_results) < 2:
            return []

        evidence_summaries = self._prepare_context(source_results)
        prompt = self._build_prompt(query, evidence_summaries)

        try:
            kwargs = dict(
                model=settings.REAL_LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            model_name = settings.REAL_LLM_MODEL.lower()
            if "gpt" in model_name or "deepseek" in model_name:
                kwargs["response_format"] = {"type": "json_object"}
            response = await self.client.chat.completions.create(**kwargs)
            data = json.loads(response.choices[0].message.content)
            return data.get("conflicts", [])
        except Exception as e:
            logger.error(f" [Detector] LLM Conflict Detection Failed: {e}")
            return []

    def _prepare_context(self, source_results: List[Dict]) -> List[Dict]:
        """准备用于 LLM 的上下文摘要"""
        summaries = []
        for result in source_results:
            chunk_texts = [f"[ID:{c['id']}][P{c['page_number']}] {c['content'][:settings.CONTEXT_EVIDENCE_CONTENT_PREFIX]}..."
                          for c in result['evidence_chunks'][:settings.CONTEXT_FALLBACK_CHUNKS]]
            summaries.append({
                "source_name": result["source_name"],
                "doc_id": (result.get("doc_id") or "")[:settings.CONTEXT_COMMIT_DOC_ID_PREFIX],
                "evidence_summary": "\n".join(chunk_texts)
            })
        return summaries

    def _build_prompt(self, query: str, summaries: List[Dict]) -> str:
        """构建冲突检测的 Prompt (从原代码迁移并解耦)"""
        return f"""You are a rigorous logic auditor. Please analyze the following evidence, detect logical conflicts.

【Original Query】
{query}

【Source Results List】
{json.dumps(summaries, ensure_ascii=False, indent=2)}

Your tasks:
1. Extract core claims (factual statements) from each source result
2. Identify contradictions or inconsistencies between claims
3. If no obvious conflicts, return empty list
4. 【V7.0 Strict Mode】If conflicts/relationships detected, must declare proposed_relationships

【Relationship Type Definitions】(strict enum, no custom types)
- causality: A causes B, or A is a prerequisite for B
- contradiction: A logically conflicts with B (needs resolution)
- support: A provides physical-level evidence support for B
- evolution: B is a correction of A (cross-document knowledge evolution)
- complement: A and B describe different dimensions of the same entity

Output format (strict JSON）：
{{
    "conflicts": [
        {{
            "description": "Conflict description",
            "packages": [
                {{"source_name": "Source Name", "doc_id": "Document ID", "claim": "Claim content", "chunk_id": "Chunk ID"}}
            ],
            "severity": "CRITICAL" or "MINOR",
            "proposed_relationships": [
                {{
                    "source_chunk_id": "Chunk ID 1",
                    "target_chunk_id": "Chunk ID 2",
                    "rel_type": "contradiction",
                    "strength": 0.95,
                    "description": "Two chunks have direct contradiction on XX description"
                }}
            ]
        }}
    ]
}}

Note:
- proposed_relationships is optional, only declare when you are certain relationships exist
- rel_type must be one of the above enum values
- strength range 0.0-1.0
- chunk_id must be the actual chunk ID from [ID:...] prefix (e.g., [ID:recXXXX] → chunk_id = "recXXXX")
- Do not force finding conflicts! If no obvious contradiction, return empty list!
"""
