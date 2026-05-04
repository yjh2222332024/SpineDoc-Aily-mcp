"""
SynthesizerNode - The Final Judge & Narrative Weaver
===================================================
Responsibility:
1. Analyze the audited evidence pool and weighted claims.
2. Produce an internal 'Objective Verdict' for knowledge evolution.
3. Formulate a conversational 'Assistant Response' for the end user.
4. Resolve final conflicts based on the Sovereignty-first principle.
"""

import logging
from typing import Dict, Any, List
from backend.app.services.ingestion.llm_service import llm_service
from .schema import CourtState

logger = logging.getLogger(__name__)

class SynthesizerNode:
    """
    🚀 [V190.0] 终极裁定节点：区分‘绝对客观真理’与‘用户交互陈述’。
    """
    async def synthesize(self, state: CourtState) -> Dict[str, Any]:
        print(f"⚖️ [SynthesizerNode] 首席法官入场，准备签署最终判决书...")
        
        # 1. 准备庭审材料
        # 只取高权重（> 0.4）的精华主张
        weights = state.get("claim_weights", {})
        evidence_pool = state.get("evidence_pool", [])
        active_evidence = [e for e in evidence_pool if weights.get(e["id"], 1.0) >= 0.4]
        
        # 2. 构造判决 Prompt
        prompt = f"""请作为联邦法院首席法官，根据以下经过审计的证据，签署最终裁定。

【用户的原始质询】：
{state['query']}

【质证证据清单】：
{self._format_evidence_for_judge(active_evidence, weights)}

你的任务：
1. 提取【内部共识】(Internal Consensus)：这是一组绝对客观、无修辞的原子事实，用于系统知识库的更新。
2. 撰写【助手回答】(Assistant Answer)：这是一段对用户友好的、丝滑的自然语言陈述，必须包含对信源的引用（如 [本地主权] 或 [联网证人]）。
3. 如果存在无法解决的冲突，请在【冲突备忘】中列出。

请严格输出 JSON 格式：
{{
    "internal_consensus": ["原子事实1", "原子事实2"],
    "assistant_answer": "给用户的丝滑回答...",
    "unresolved_conflicts": ["未解决的争议点..."],
    "citations": ["id1", "id2"]
}}
"""
        try:
            # 🚀 物理裁定：执行双路输出合成
            verdict = await llm_service.chat_completion(prompt, response_format="json")

            print(f"🏁 [SynthesizerNode] 判决签署完成。包含 {len(verdict.get('internal_consensus', []))} 条客观真理。")

            # 用 AnswerBuilder 生成用户友好回答（Mentor/Chief Registrar 双人格）
            from ..answer_builder import AnswerBuilder
            builder = AnswerBuilder()

            # 构建 source_results 格式给 AnswerBuilder
            source_results = []
            src_map: Dict[str, Dict] = {}
            for e in evidence_pool:
                src_name = e.get("source_name", "Unknown")
                if src_name not in src_map:
                    src_map[src_name] = {
                        "source_name": src_name,
                        "doc_id": e.get("doc_id", ""),
                        "evidence_chunks": [],
                    }
                src_map[src_name]["evidence_chunks"].append(e)
            source_results = list(src_map.values())

            user_answer = await builder.build_answer(
                query=state["query"],
                final_result={"reasoning": verdict.get("assistant_answer", "Court verdict synthesized.")},
                source_results=source_results,
                temperature=0.6
            )
            verdict["assistant_answer"] = user_answer

            return {
                "verdict": verdict,
                "next_step": "EVOLVE"
            }
        except Exception as e:
            logger.error(f"❌ [SynthesizerNode] 裁定过程崩溃: {e}")
            return {
                "final_answer": "法官由于物理原因暂时无法宣判，请重试。",
                "next_step": "END"
            }

    def _format_evidence_for_judge(self, pool: List[Dict], weights: Dict) -> str:
        lines = []
        for e in pool:
            w = weights.get(e["id"], 1.0)
            origin = "本地主权" if e.get("is_sovereign") else "联网证人"
            lines.append(f"- [{e['id']}] (来源: {origin}, 权重: {w:.2f}): {e.get('claims')}")
        return "\n".join(lines)

synthesizer_node = SynthesizerNode()
