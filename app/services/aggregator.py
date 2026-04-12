import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class KnowledgeAggregator:
    """
    🚀 [V22.0] HMAC 聚合器 (Hierarchical Multi-Agent Collaborative Aggregator)
    职责：执行多专家辩论逻辑，合成高置信度知识。
    """
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

    async def synthesize(self, query: str, evidence: List[Dict[str, Any]], spine_summary: str = "") -> str:
        """
        核心方法：执行三阶段合成
        1. 证据交叉盘问 (Cross-Examination)
        2. 逻辑漏洞识别 (Hole Identification)
        3. 最终一致性总结 (Consensus Synthesis)
        """
        if not evidence: return "未找到有效证据，无法合成回答。"

        context = "\n\n".join([f"来源：{e.get('breadcrumb','')} \n内容：{e['content']}" for e in evidence])

        # 🚀 架构师设计：使用改进版 HMAC Prompt 模板
        from spine_cli.prompts import HMAC_DEBATE_PROMPT
        
        sys_prompt = HMAC_DEBATE_PROMPT.render(
            current_date=datetime.now().strftime("%Y-%m-%d"),
            document_title="未知文档",
            evidence_count=len(evidence),
            spine_summary=spine_summary,
            context=context,
            query=query,
        )
        
        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "system", "content": sys_prompt},
                          {"role": "user", "content": query}],
                temperature=0.3
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"聚合器崩溃：{e}")
            return "合成阶段发生严重异常，请检查日志。"

# 单例
aggregator = KnowledgeAggregator()
