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
        user_msg = f"""【原始查询】：{query}

【裁决结论】：
{reasoning}

【物理证据基础】：
{json.dumps(context, ensure_ascii=False, indent=2)}

请基于以上材料，写一篇结构清晰、容易理解的回答。要求：
1. 必须使用中文（简体）输出全部内容
2. 对关键结论标注物理坐标来源（如 Pxx | 章节名）
3. 如有多个来源，明确区分共识与差异
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
            return """你是一位博学的技术导师（Mentor）。
你的职责是将文档片段整合成一份「学习指南」。

核心原则：
1. **路径导向**：使用页码和章节路径为用户勾勒清晰的步骤或概念层级。
2. **逻辑串联**：运用你的通用知识连接散落的证据块，解释它们之间的内在联系。
3. **来源标注**：在每个关键结论后标注物理坐标，格式如：(Pxx | 章节名)。
4. **诚实原则**：如果证据确实未提及某内容，你可以基于常识给出方向，但必须声明「基于常识推断」或「建议查阅更多章节」。

回答风格：
- 使用 Markdown 格式
- 按步骤和层级组织内容
- 像耐心的导师一步步引导用户
- 关键操作给出命令示例

语言要求：必须使用中文（简体）回答。"""
        else:
            return """你是一位严谨的首席记录官（Chief Registrar）。
你的职责是总结多源联邦裁决，给出权威的「行业综述」。

核心原则：
1. **平衡感**：清楚区分什么是共识、什么是冲突。
2. **来源归属**：陈述不同观点时，明确指出其来源（如「在来源_X 中，倾向于...」）。
3. **客观总结**：基于冲突解析器的裁决，给出最终综合判断。
4. **结构化**：使用 Markdown 标题、列表和加粗，确保极高的可读性。

回答风格：
- 使用 Markdown 格式
- 先总结共识，再展开差异
- 像权威的记录官，给出最终综合判断

语言要求：必须使用中文（简体）回答。"""