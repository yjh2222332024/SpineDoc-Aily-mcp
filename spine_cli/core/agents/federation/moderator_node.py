"""
SpineDoc V40.1 - ModeratorNode (Logic Assassin Edition)
=====================================================
职责：冲突检测、交叉盘问路由、三错即停。
"""
import json
import logging
from typing import List, Dict, Any, Tuple
from openai import AsyncOpenAI
from app.core.config import settings
from .state import FederatedState
from .types import AtomicClaim, CollisionPoint, ModeratorDecision
from collections import defaultdict

logger = logging.getLogger(__name__)

MODERATOR_SYSTEM_PROMPT = """你是一个冷酷的【逻辑法官】。你的唯一任务是审查多个证人的证词，并找出其中的冲突点。

【负向约束指令】：
1. 🛑 禁止合成 (No Synthesis)：严禁在此时生成最终答案。
2. 🛑 禁止调解 (No Mediation)：如果 A 和 B 冲突，严禁尝试通过“可能”、“或者”来和稀泥。
3. 🛑 禁止主观 (No Subjectivity)：只对比事实文本的差异。

【冲突识别准则】：
- 物理矛盾：同一页码 (Pxx) 下，论点 A 与论点 B 描述不一。
- 数据矛盾：数值、日期、名称、特征等硬事实不匹配（例如 A 说 64 位，B 说 128 位）。
- 逻辑断层：A 提到 B 必须存在，但所有证词中均未发现 B。

【输出格式 (JSON ONLY)】：
{
  "status": "CONSENSUS | CONFLICT | INSUFFICIENT",
  "collisions": [
    {
      "point": "简述冲突点（例如：关于分组长度的数值矛盾）", 
      "witnesses": ["DOC_1", "DOC_2"], 
      "evidence": "DOC_1 说 64 位，DOC_2 说 128 位"
    }
  ],
  "next_step": "REFINE | DONE | ERROR"
}
"""

async def detect_collisions_layered(claims_by_witness: Dict[str, List[AtomicClaim]], query: str) -> List[CollisionPoint]:
    """
    🚀 [V40.1] 分层冲突检测：规则对线 + 语义扫描
    """
    collisions = []
    
    # --- Step 1: 物理页码对线 (Rule-based) ---
    page_map = defaultdict(list)
    for agent_id, claims in claims_by_witness.items():
        for c in claims:
            page_map[c.page].append(c)
            
    for page, claims in page_map.items():
        if len(claims) > 1:
            # 检查文本是否高度相似 (简单实现：排除完全一致)
            unique_contents = list(set([c.content for c in claims]))
            if len(unique_contents) > 1:
                collisions.append(CollisionPoint(
                    collision_type="PAGE_CONFLICT",
                    description=f"物理页码 P{page} 存在描述不一致",
                    involved_witnesses=list(set([c.witness_id for c in claims])),
                    evidence_claims=claims,
                    severity=0.8
                ))

    # 如果物理对线已经发现致命冲突，优先处理
    if any(c.severity >= 0.8 for c in collisions):
        return collisions

    # --- Step 2: 语义冲突检测 (LLM-based) ---
    # 仅当规则层未发现冲突时，启动 LLM 深度扫描逻辑差异
    debate_context = ""
    for agent_id, claims in claims_by_witness.items():
        debate_context += f"--- 证人 {agent_id} 的证词 ---\n"
        for c in claims:
            debate_context += f"[CLAIM] P{c.page}: {c.content}\n"
            
    client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
    try:
        res = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": MODERATOR_SYSTEM_PROMPT},
                {"role": "user", "content": f"用户问题：{query}\n\n当前所有证词：\n{debate_context}"}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        decision = json.loads(res.choices[0].message.content)
        
        for col in decision.get("collisions", []):
            collisions.append(CollisionPoint(
                collision_type="VALUE_CONFLICT",
                description=col.get("point", "未知语义冲突"),
                involved_witnesses=col.get("witnesses", []),
                evidence_claims=[], # 简化版暂不回溯具体 claim 对象
                severity=1.0
            ))
            
        return collisions
    except Exception as e:
        logger.error(f"LLM 冲突检测失败: {e}")
        return []

async def moderator_node(state: FederatedState) -> Dict[str, Any]:
    """
    主理人节点：执行逻辑冲突检测与路由。
    """
    if state.get("loop_count", 0) >= 3:
        print("🚨 [Logic Assassin] 逻辑死循环检测：连续 3 次辩论未果，触发熔断停机！")
        return {"last_status": "FATAL_LOGIC_STUCK", "is_sufficient": False}

    witness_data = state.get("witness_opinions", {})
    if not witness_data:
        return {"last_status": "EMPTY_EVIDENCE", "is_sufficient": False}
    
    # 1. 执行分层检测
    collisions = await detect_collisions_layered(witness_data, state['query'])
    
    # 2. 决策路由
    status = "CONFLICT" if collisions else "CONSENSUS"
    
    # 3. 生成质询问题 (Refine Questions)
    refine_questions = []
    for col in collisions:
        for wid in col.involved_witnesses:
            # 简化版：向涉及冲突的每个证人发问
            refine_questions.append({
                "target": wid,
                "question": f"关于冲突点『{col.description}』，请重新核对你的原文证据，确保数值或事实的绝对准确性。"
            })

    print(f"⚖️ [Moderator] 审查完成。状态: {status} | 冲突点: {len(collisions)}")

    # 兼容输出序列化格式
    collision_points_out = []
    for c in collisions:
        cdict = c.__dict__.copy()
        # 处理嵌套的 Dataclass 列表序列化问题
        cdict["evidence_claims"] = [ac.__dict__ for ac in cdict.get("evidence_claims", [])]
        collision_points_out.append(cdict)

    return {
        "collision_points": collision_points_out,
        "refine_questions": refine_questions,
        "last_status": status,
        "loop_count": state.get("loop_count", 0) + 1,
        "is_sufficient": status == "CONSENSUS"
    }
