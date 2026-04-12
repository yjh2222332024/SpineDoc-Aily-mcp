"""
SpineDoc V40.3 - IntegratorNode (Chief Justice Edition)
======================================================
职责：将经过辩论、对线、核实的原子事实合成为最终判决书。
"""
import json
import logging
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
from app.core.config import settings
from .state import FederatedState

logger = logging.getLogger(__name__)

INTEGRATOR_SYSTEM_PROMPT = """你是一个冷静、严谨的【联邦首席大法官】。
你的任务是根据多名证人提供的【原子事实】以及主理人发现的【冲突报告】，撰写一份最终知识判决书及量化执行指令。

【输出格式要求 (必须是合法 JSON)】：
{
  "verdict_markdown": "# 知识判决书\\n...", 
  "decision": {
    "action": "BUY | SELL | HOLD | WAIT",
    "confidence_score": 0.85,
    "logic_summary": "简述决策逻辑"
  },
  "grounding_map": [
    {"claim": "事实描述", "color": "GREEN | BLUE | YELLOW | RED", "source": "Pxx / URL"}
  ]
}

【判定准则】：
1. 🟢 GREEN (Internal): 来源于用户 PDF 且无冲突。
2. 🟦 BLUE (External): 来源于互联网且印证了 PDF 或补充了盲区。
3. 🟨 YELLOW (Outdated): 内部 PDF 已过时，互联网有更新。
4. 🟥 RED (Conflict): 严重冲突且无法调解。

【负向约束指令】：
1. 🛑 禁止合成 (No Synthesis)：严禁在此时生成最终答案。
2. 🛑 禁止调解 (No Mediation)：如果 A 和 B 冲突，严禁尝试通过“可能”、“或者”来和稀泥。
3. 🛑 禁止主观 (No Subjectivity)：只对比事实文本的差异。
"""

async def integrator_node(state: FederatedState, override_api_key: Optional[str] = None) -> Dict[Any, Any]:
    """
    首席大法官：合成最终回答。
    """
    # 🚀 [V1.3.1] 支持动态 API Key
    request_api_key = override_api_key or settings.LLM_API_KEY
    opinions = state.get("witness_opinions", {})
    collisions = state.get("collision_points", [])
    
    # 格式化所有事实素材
    evidence_context = ""
    for wid, claims in opinions.items():
        evidence_context += f"### 证人 {wid} 的最终证言：\n"
        evidence_context += "\n".join([c.raw_text for c in claims]) + "\n\n"
    
    if collisions:
        evidence_context += "### 待核实的冲突报告 (Logic Collisions)：\n"
        # 🚀 [V40.8 Fix] 手动格式化冲突报告，避开 JSON 序列化枚举的坑
        for i, col in enumerate(collisions):
            evidence_context += f"{i+1}. 冲突点：{col.get('description')}\n"
            evidence_context += f"   - 涉事方：{', '.join(col.get('involved_witnesses', []))}\n"
            evidence_context += f"   - 矛盾证据片段：{col.get('evidence')}\n"

    client = AsyncOpenAI(api_key=request_api_key, base_url=settings.LLM_BASE_URL)
    
    try:
        res = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": INTEGRATOR_SYSTEM_PROMPT},
                {"role": "user", "content": f"用户问题：{state['query']}\n\n所有核实过的证据：\n{evidence_context}"}
            ],
            response_format={"type": "json_object"}, # 🚀 强制结构化输出
            temperature=0.1 # 极低温度保持严谨
        )
        
        # 解析结构化判决书
        raw_verdict = json.loads(res.choices[0].message.content)
        final_verdict_md = raw_verdict.get("verdict_markdown", "未能生成有效的判决书文本。")
        
        print(f"⚖️ [Chief Justice] 结构化判决书合成完毕。")
        
        return {
            "final_answer": final_verdict_md, # 保持对现有 CLI 的兼容
            "structured_verdict": raw_verdict, # 🚀 为 Web 和量化引擎提供全量数据
            "last_status": "DONE",
            "is_sufficient": True
        }
    except Exception as e:
        logger.error(f"大法官合成崩溃: {e}")
        return {"last_status": "INTEGRATION_ERROR", "error": str(e)}
