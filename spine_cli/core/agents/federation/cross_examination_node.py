"""
SpineDoc V40.2 - CrossExaminationNode (Backtrack Edition)
========================================================
职责：将冲突点反馈给证人，并携带原始证据与完整语境，强制其进行事实核对。
"""
from typing import Dict, Any, List
from .witness_node import witness_node
from .state import FederatedState
import asyncio

async def cross_examination_node(state: FederatedState) -> Dict[str, Any]:
    """
    交叉盘问：携带原始证据进行二次事实确认。
    """
    refine_tasks = state.get("refine_questions", [])
    if not refine_tasks:
        return {"last_status": "NO_REFINE_NEEDED"}

    print(f"🔄 [Cross-Exam] 启动 V40.2 增强版交叉盘问，涉及 {len(refine_tasks)} 个质疑点...")
    
    # 获取锁存的原始证据和之前的论点
    original_contexts = state.get("witness_contexts", {})
    original_opinions = state.get("witness_opinions", {})
    
    updated_opinions = original_opinions.copy()
    
    async def process_refine(task):
        wid = task["target"]
        question = task["question"]
        
        # 1. 提取该证人的原始原文
        raw_source = original_contexts.get(wid, "未找到原始证据")
        
        # 2. 提取该证人之前的论点
        prev_claims = "\n".join([c.raw_text for c in original_opinions.get(wid, [])])
        
        # 3. 构造增强质询语境 (符合证人的负向约束)
        backtrack_context = f"""【你的原始证据原文】
{raw_source}

【你之前的论点】
{prev_claims}

【主理人质疑与冲突提示】
{question}

【任务】
请对照【原始证据原文】，重新核实你的论点。
如果原文确实支持之前的论点，请通过 [CONFIRM] (Pxx) 再次确认。
如果原文显示之前论点有误，请通过 [CORRECT] (Pxx) 修正。
严禁为了迎合主理人而编造事实！
"""
        # 重新调用证人节点
        new_claims = await witness_node(
            query=state["query"],
            context=backtrack_context,
            agent_id=wid
        )
        return wid, new_claims

    # 并发执行回溯质询
    results = await asyncio.gather(*[process_refine(t) for t in refine_tasks])
    
    for wid, claims in results:
        if claims:
            updated_opinions[wid] = claims

    return {
        "witness_opinions": updated_opinions,
        "last_status": "REFINE_COMPLETED"
    }
