"""
🖋️  Synthesizer - 联邦法庭外交官
================================
职责：接收法官裁决与原始证据，产出具备高可读性的"人话"答案。
模式：根据证据包数量自动切换"导读员"与"记录官"人格。

架构哲学 (Uncle Bob, 2026-04-16):
    大法官必须要维持 0.1 的低温以防幻觉。
    外交官需要 0.7 的灵魂温度来进行"语义联想与缝合"。
    抽象问题（如"0 基础入门"）需要模型进行创造性整合。
"""

import json
import logging
from typing import List, Dict, Any
from openai import AsyncOpenAI
from backend.app.core.config import settings

logger = logging.getLogger(__name__)


class Synthesizer:
    """
    🖋️ 外交官 (The Synthesizer)

    职责：
    1. 接收法官裁决与原始证据
    2. 根据证据包数量自动切换人格
    3. 产出具备高可读性的"人话"答案
    """

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL
        )

    async def weave_answer(
        self,
        query: str,
        verdict: Dict,
        evidence_packages: List[Dict],
        temperature: float = 0.6
    ) -> str:
        """
        核心外交逻辑：串联逻辑孤岛，抹平主观题焦虑。

        Args:
            query: 原始问题
            verdict: 法官裁决书
            evidence_packages: 证据包列表
            temperature: 灵魂温度 (0.6-0.7 用于创造性整合)

        Returns:
            整合后的答案字符串
        """
        print(f"🖋️  [Synthesizer] 正在以模式 {'SINGLE' if len(evidence_packages)==1 else 'MULTI'} 整合答案...")

        # 1. 准备外交上下文
        context = self._prepare_context(evidence_packages)
        adjudication = verdict.get("reasoning", "无冲突或已达成共识。")

        # 2. 确定人格与指令
        is_single = len(evidence_packages) == 1
        system_prompt = self._get_persona_prompt(is_single)

        # 3. 构造请求
        user_msg = f"""【原始问题】：{query}

【法庭裁决结论】：
{adjudication}

【物理证据库】：
{json.dumps(context, ensure_ascii=False, indent=2)}

请基于以上材料，为用户写出一份结构清晰、通俗易懂的答案。
"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg}
                ],
                temperature=temperature
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Synthesizer 崩溃：{e}")
            return verdict.get("final_answer", "外交官暂时无法工作，请参阅法庭原始判决。")

    def _prepare_context(self, packages: List[Dict]) -> List[Dict]:
        """
        提取带有坐标感的证据精华

        Args:
            packages: 证据包列表

        Returns:
            简化后的上下文列表
        """
        simplified_context = []
        for pkg in packages:
            chunks = []
            for c in pkg.get("evidence_chunks", []):
                chunks.append({
                    "p": c.get("page_number"),
                    "path": c.get("breadcrumb"),
                    "content": c.get("content")
                })
            simplified_context.append({
                "source": pkg.get("galaxy_name", "未知星系"),
                "evidence": chunks
            })
        return simplified_context

    def _get_persona_prompt(self, is_single: bool) -> str:
        """
        根据证据包数量切换人格

        Args:
            is_single: 是否为单文档模式

        Returns:
            System prompt 字符串
        """
        if is_single:
            return """你是一个博学的技术导师（Mentor）。
你的职责是把枯燥的文档片段整合成一份'学习指南'。

核心原则：
1. **路径化**：利用页码和章节路径，为用户梳理出清晰的步骤或概念层次。
2. **粘合逻辑**：利用你的通用知识，把分散的证据块串联起来，解释它们之间的内在联系。
3. **标注出处**：在每个关键结论后，必须标注物理坐标，格式如：(Pxx | 章节名)。
4. **诚实原则**：如果证据确实没提到，可以基于常识给出方向，但必须声明'根据常识推测'或'建议查阅更多章节'。

回答风格：
- 使用 Markdown 格式
- 分步骤、分层次组织内容
- 像一位耐心的导师，引导用户循序渐进
- 关键操作要给出命令示例"""
        else:
            return """你是一个严谨的首席记录官（Chief Registrar）。
你的职责是汇总多个星系的联邦判决，给出权威的'行业综述'。

核心原则：
1. **权衡感**：明确区分哪些是共识，哪些是冲突。
2. **星系归属**：在陈述不同观点时，明确指出其来源星系（例如：'在 Galaxy_Crypto 星系中倾向于...'）。
3. **客观总结**：基于 Moderator 的裁决，给出一个最终的综合判定。
4. **结构化**：使用 Markdown 标题、列表和加粗，让答案具备极高的可读性。

回答风格：
- 使用 Markdown 格式
- 先总结共识，再阐述分歧
- 像一位权威的记录官，给出最终的综合判定"""
