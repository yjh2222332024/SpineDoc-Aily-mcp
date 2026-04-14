from langgraph.graph import StateGraph, END
from .state import WitnessState
from .nodes import (
    scout_node,
    witness_collector_node,
    examiner_node,
    integrator_node
)

def create_witness_graph():
    """
    🚀 SpineDoc 单文档证人图谱 - V3.5 质证版
    职责：执行“拆解-收割-质证-合成”的单文档全生命周期推理。
    """
    workflow = StateGraph(WitnessState)
    
    # 1. 注册核心节点
    workflow.add_node("scout", scout_node)
    workflow.add_node("witness_collector", witness_collector_node)
    workflow.add_node("examiner", examiner_node)
    workflow.add_node("integrator", integrator_node)
    
    # 2. 设置入口
    workflow.set_entry_point("scout")
    
    # 3. 建立确定性流水线 (线性逻辑，重点在于节点内部的复杂性)
    workflow.add_edge("scout", "witness_collector")
    workflow.add_edge("witness_collector", "examiner")
    workflow.add_edge("examiner", "integrator")
    workflow.add_edge("integrator", END)
    
    return workflow.compile()

# 单例导出
witness_graph = create_witness_graph()
