import json
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.core.config import settings

class NexusExtractor:
    """
    NexusExtractor V35.0: 万物互联原子提取器
    职责：对每一个分块执行多维逻辑审计，提取标签、因果链和置信度。
    """
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

    async def extract_nexus_data(self, content: str, context: str = "") -> Dict[str, Any]:
        """
        🚀 [V36.1] 真实逻辑审计：提取因果链与动态置信度
        """
        prompt = f"""你是一个顶级的逻辑审计专家。分析片段，提取因果脉络。
背景：{context}
文本：{content}

任务：
1. 提取【逻辑标签】（用于跨文档索引）。
2. 识别【因果链】：该片段在逻辑上【暗示】(implies)什么？是否与某些常识或已知逻辑【冲突】(conflicts)？
3. 评估【置信度】：0.0-1.0。原文越直接，分数越高。

输出 JSON: {{
  "tags": [],
  "causality": {{"implies": [], "conflicts": [], "rationale": ""}},
  "confidence": 0.95
}}"""
        try:
            res = await self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" },
                temperature=0
            )
            import json
            data = json.loads(res.choices[0].message.content)
            # 🚀 真实注入
            return {
                "logic_tags": data.get("tags", []),
                "causality_links": data.get("causality", {}),
                "confidence_score": float(data.get("confidence", 0.8))
            }
        except:
            return {"logic_tags": [], "causality_links": {}, "confidence_score": 0.5}

    async def generate_global_atlas(self, doc_summary: str, all_tags: List[str]) -> Dict[str, Any]:
        """
        为整份文档生成全局 Nexus 画像
        """
        prompt = f"""你是一个知识图谱专家。请为这份文档生成全局逻辑画像。
文档摘要：{doc_summary}
提取的所有标签：{list(set(all_tags))[:50]}

请输出该文档在全景知识库中的逻辑位置（Atlas）：
{{
  "domain": "所属领域",
  "logical_center": "核心逻辑点",
  "cross_links": ["可能关联的其他领域"]
}}
"""
        try:
            res = await self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" },
                temperature=0
            )
            return json.loads(res.choices[0].message.content)
        except:
            return {"domain": "Unknown", "logical_center": "General"}
