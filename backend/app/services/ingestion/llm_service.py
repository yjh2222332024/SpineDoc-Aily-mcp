"""
SpineDoc Centralized LLM Service
===============================
Responsibility: Provide high-level LLM capabilities (chat, extraction) using the centralized client.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from backend.app.infra.llm_client import get_llm_client
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self):
        self.client = get_llm_client()
        self.model = settings.REAL_LLM_MODEL

    async def chat_completion(self, prompt: str, system_prompt: str = "You are a helpful assistant.", response_format: str = "text") -> Any:
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.1
            }
            
            # 🚀 [V110.1] 兼容性重构：由于部分模型不支持 json_object 参数
            # 我们通过 Prompt 强制约束并在代码中执行提取

            resp = await self.client.chat.completions.create(**kwargs)
            content = resp.choices[0].message.content
            
            if response_format == "json":
                # 🛡️ 鲁棒性提取：处理可能带 Markdown 代码块的返回
                json_match = re.search(r'(\{.*\}|\[.*\])', content, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
                return json.loads(content)
            return content
        except Exception as e:
            logger.error(f"❌ [LLMService] Request failed: {e}")
            raise

import re
llm_service = LLMService()
