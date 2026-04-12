from langgraph.graph import StateGraph, END
from .state import FederatedState
from .witness_node import witness_node
from .quant_market_witness import quant_market_witness_node
from .moderator_node import moderator_node
from .cross_examination_node import cross_examination_node
from .integrator_node import integrator_node
from typing import Dict, Any

def debate_routing(state: FederatedState):
    """
    逻辑刺客路由：
    1. 达成共识 (CONSENSUS) -> 结案陈词 (integrator)
    2. 发现冲突 (CONFLICT) 且次数 < 3 -> 继续对线 (cross_exam)
    3. 冲突严重或次数 >= 3 -> 强制熔断，提交残缺证据 (integrator)
    """
    if state.get("is_sufficient") or state.get("last_status") == "CONSENSUS":
        return "integrator"
    
    if state.get("loop_count", 0) >= 3:
        print("🚨 [Logic Assassin] 已达辩论上限，强制进入最终判决。")
        return "integrator"
    
    if state.get("last_status") == "CONFLICT":
        return "cross_exam"
    
    return "integrator"

async def entry_distributor_node(state: FederatedState):
    """
    入场分发：将 initial_hits 按文档分组，发起第一轮蒙眼取证。
    🚀 [V41.6] 并行集成：同时拉起 PDF 证人和 实时市场证人。
    """
    from collections import defaultdict
    doc_groups = defaultdict(list)
    for hit in state.get("initial_hits", []):
        doc_groups[str(hit.get("document_id"))].append(hit)
    
    import asyncio
    
    # --- Task 1: 市场证人 (Quant Market) ---
    market_task = quant_market_witness_node(state)
    
    # --- Task 2: PDF 证人们 ---
    async def run_one_witness(doc_id, hits):
        context = "\n".join([f"P{h.get('page_number')}: {h.get('content', h.get('text'))}" for h in hits])
        claims = await witness_node(state['query'], context, doc_id[:8])
        return doc_id, claims, context

    witness_tasks = [run_one_witness(d_id, hits) for d_id, hits in doc_groups.items()]
    
    # 🚀 并行收割所有证据
    results = await asyncio.gather(market_task, *witness_tasks)
    
    # 第一个结果是 market_node 的字典
    market_res = results[0]
    opinions = market_res.get("witness_opinions", {})
    contexts = market_res.get("witness_contexts", {})
    
    # 后续结果是 (doc_id, claims, context) 元组
    for doc_res in results[1:]:
        if not doc_res: continue
        d_id, claims, ctx = doc_res
        opinions[d_id] = claims
        contexts[d_id] = ctx
        
    return {
        "witness_opinions": opinions,
        "witness_contexts": contexts,
        "loop_count": 0
    }

def create_federated_graph():
    workflow = StateGraph(FederatedState)
    
    # 1. 注册节点
    workflow.add_node("distributor", entry_distributor_node)
    workflow.add_node("moderator", moderator_node)
    workflow.add_node("cross_exam", cross_examination_node)
    workflow.add_node("integrator", integrator_node)
    
    # 2. 建立连线
    workflow.set_entry_point("distributor")
    workflow.add_edge("distributor", "moderator")
    
    # 3. 条件路由
    workflow.add_conditional_edges(
        "moderator",
        debate_routing,
        {
            "cross_exam": "cross_exam",
            "integrator": "integrator"
        }
    )
    
    workflow.add_edge("cross_exam", "moderator") # 🔄 形成对线闭环
    workflow.add_edge("integrator", END)
    
    return workflow.compile()
