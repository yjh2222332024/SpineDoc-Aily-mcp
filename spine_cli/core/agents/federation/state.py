from typing import List, Dict, Any, TypedDict, Optional
from .types import AtomicClaim, CollisionPoint

class FederatedState(TypedDict):
    """
    SpineDoc V40.2 联邦辩论状态 - 强类型回溯版
    """
    # 基础信息
    query: str
    doc_ids: List[str]
    doc_paths: Dict[str, str]
    
    # 初始线索
    initial_hits: List[Dict[str, Any]]
    
    # 🆕 证据锁存：存储每个证人看到的原始原文，用于交叉盘问回溯
    witness_contexts: Dict[str, str] 
    
    # 辩论上下文 (已升级为强类型)
    witness_opinions: Dict[str, List[AtomicClaim]] 
    collision_points: List[Dict[str, Any]] # 存储字典化的 CollisionPoint 方便序列化
    
    # 质询路由
    refine_questions: List[Dict[str, str]]
    
    # 熔断控制
    loop_count: int
    error_count: int
    last_status: str
    
    # 最终产出
    pro_evidence: List[Dict[str, Any]]
    final_answer: str
    is_sufficient: bool

def create_initial_state(query: str, doc_ids: List[str], doc_paths: Dict[str, str]) -> FederatedState:
    return {
        "query": query,
        "doc_ids": doc_ids,
        "doc_paths": doc_paths,
        "initial_hits": [],
        "witness_contexts": {}, # 初始化为空
        "witness_opinions": {},
        "collision_points": [],
        "refine_questions": [],
        "loop_count": 0,
        "error_count": 0,
        "last_status": "START",
        "pro_evidence": [],
        "final_answer": "",
        "is_sufficient": False
    }
