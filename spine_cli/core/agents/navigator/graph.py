from langgraph.graph import StateGraph, END
from .state import NavigatorState
from .nodes import (
    cartographer_node, 
    field_investigator_node, 
    grader_critic_node,
    rewriter_node,
    editor_node
)

def routing_logic(state: NavigatorState):
    """
    SOTA 路由逻辑：判断是继续迭代还是结束任务。
    """
    if state.get("is_sufficient"):
        return "editor"
    
    if state.get("hop_count", 0) >= 3:
        print("⚠️ [Navigator] 已达到最大跳数 (3)，强制进入合成阶段。")
        return "editor"
    
    return "rewriter"

def create_navigator_graph():
    """
    Spine-Navigator SOTA 迭代图谱 V28.0
    工作流：Distiller -> Investigator -> Grader -> (Rewriter -> Distiller) | Editor
    """
    workflow = StateGraph(NavigatorState)
    
    # 1. 注册节点
    workflow.add_node("distiller", cartographer_node)
    workflow.add_node("investigator", field_investigator_node)
    workflow.add_node("grader", grader_critic_node)
    workflow.add_node("rewriter", rewriter_node)
    workflow.add_node("editor", editor_node)
    
    # 2. 设置入口
    workflow.set_entry_point("distiller")
    
    # 3. 建立静态边
    workflow.add_edge("distiller", "investigator")
    workflow.add_edge("investigator", "grader")
    workflow.add_edge("rewriter", "distiller") # 🔄 闭环：重新搜索
    workflow.add_edge("editor", END)
    
    # 4. 建立条件边 (SOTA 核心)
    workflow.add_conditional_edges(
        "grader",
        routing_logic,
        {
            "rewriter": "rewriter",
            "editor": "editor"
        }
    )
    
    return workflow.compile()
