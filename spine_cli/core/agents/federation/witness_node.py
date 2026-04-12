"""
SpineDoc V40.1 - WitnessNode (Logic Assassin Edition)
===================================================
职责：执行物理取证，绝对客观，禁止推理。
"""
import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# 🚀 [PROMPT] 负向约束指令集
WITNESS_SYSTEM_PROMPT = """你是一个零情感、高精度的【证据提取机】。你的任务是基于局部片段生成“原子论点（Atomic Claims）”。

【核心目标】：
根据用户问题，从证据片段中提取一切相关的硬事实。哪怕片段中只包含问题的一部分信息（例如问题问 A 和 B，片段只提到 A），你也必须把 A 的事实提取出来！绝不能因为信息不全而放弃提取。

【负向约束指令 (Strictly Forbidden)】：
1. 🛑 禁止总结 (No Summarization)：严禁对内容进行概括，必须按原文事实呈现。
2. 🛑 禁止联想 (No Association)：严禁通过逻辑推导建立因果关系，除非原文直接说明。
3. 🛑 禁止情感 (No Emotion)：禁止使用主观评估色彩的词汇。
4. 🛑 禁止外推 (No Extrapolation)：严禁使用外部模型知识。只提取原文确实存在的内容。
5. 🛑 禁止无锚点 (No Anchorless)：每一个论点必须挂载 Physical Page (Pxx)。

【输出格式】：
[CLAIM-1] (Pxx) 事实描述
[CLAIM-2] (Pyy) 事实描述
...
如果片段中连一丁点与问题相关的字眼都没有，才输出：[STATUS: NO_EVIDENCE]
"""

import re
from .types import AtomicClaim, ClaimType

# 🚀 [V40.2] 鲁棒性正则解析集 (支持回溯标签)
CLAIM_PATTERNS = [
    r'\[(CLAIM|CONFIRM|CORRECT)[-_]?\d*\]\s*\(P(\d+)\)\s*(.+)',  
    r'\[(CLAIM|CONFIRM|CORRECT)[-_]?\d*\]\s*P(\d+)[：:]\s*(.+)',    
    r'\(P(\d+)\)\s*(.+)',                         
]

def parse_atomic_claims(content: str, agent_id: str) -> List[AtomicClaim]:
    """
    [V40.7] 鲁棒原子论点解析器：安全处理多种正则模式。
    """
    claims = []
    lines = content.split("\n")
    
    for line in lines:
        line = line.strip()
        if not line or "[STATUS:" in line:
            continue
            
        for pattern in CLAIM_PATTERNS:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                try:
                    # 🚀 [V40.7 Fix] 动态分组判断，消除 IndexError 风险
                    groups = match.groups()
                    if len(groups) >= 3: # 匹配带标签模式 (CLAIM|CONFIRM|CORRECT)
                        # groups[0] 是标签，groups[1] 是页码，groups[2] 是内容
                        p_num = int(groups[1])
                        text = groups[2].strip()
                    elif len(groups) >= 2: # 匹配纯 (Pxx) 模式
                        # groups[0] 是页码，groups[1] 是内容
                        p_num = int(groups[0])
                        text = groups[1].strip()
                    else:
                        continue
                        
                    claims.append(AtomicClaim(
                        content=text,
                        page=p_num,
                        witness_id=agent_id,
                        raw_text=line
                    ))
                    break 
                except (ValueError, IndexError) as e:
                    logger.warning(f"⚠️ [Parser] 行解析跳过: {line} -> {e}")
                    continue
    
    # 🆕 增强调试输出
    if claims:
        print(f"🔍 [Parser] 证人 {agent_id} 解析成功: {len(claims)} 条论点")
        for c in claims:
            print(f"   └─ [P{c.page}] {c.content[:50]}...")
            
    return claims

async def witness_node(query: str, context: str, agent_id: str, override_api_key: Optional[str] = None) -> List[AtomicClaim]:
    """
    独立证人取证。隔离环境，防止受其他文档干扰。
    """
    # 🚀 [V1.3.1] 支持动态 API Key 注入
    request_api_key = override_api_key or settings.LLM_API_KEY
    client = AsyncOpenAI(api_key=request_api_key, base_url=settings.LLM_BASE_URL)
    
    # 模拟“蒙眼”环境：仅告知当前片段
    user_prompt = f"问题：{query}\n\n你的局部证据库：\n{context}"
    
    try:
        res = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": WITNESS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0, 
            max_tokens=800
        )
        content = res.choices[0].message.content.strip()
        
        if "[STATUS: NO_EVIDENCE]" in content:
            return []
            
        print(f"\n[DEBUG] 证人 {agent_id} 原始输出:\n{content}\n")
        # 🚀 [P0] 鲁棒性解析
        return parse_atomic_claims(content, agent_id)
    except Exception as e:
        print(f"❌ [DEBUG] 证人 {agent_id} 取证崩溃: {e}")
        logger.error(f"证人 {agent_id} 取证崩溃: {e}")
        return []
