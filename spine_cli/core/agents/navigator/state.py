from typing import List, Dict, Any, TypedDict, Optional

class NavigatorState(TypedDict):
    # 🚀 [V32.0] 输入升级：支持多文档
    query: str
    doc_ids: List[str]                  # 从单 ID 升级为 ID 列表
    doc_paths: Dict[str, str]           # ID -> 路径的映射
    tocs: Dict[str, List[Dict]]         # 每个文档的逻辑脊梁
    
    # 级联过滤
    initial_hits: List[Dict[str, Any]]  # 全局混合检索结果
    target_coordinates: List[Dict]      # 选出的物理坐标 [{"doc_id":..., "page":...}]
    
    # 辩论状态
    hop_count: int
    pro_evidence: List[Dict]            # 支撑性证据
    con_evidence: List[Dict]            # 反驳性证据
    gaps: str
    
    # 最终结果
    final_answer: str
    is_complex: bool
