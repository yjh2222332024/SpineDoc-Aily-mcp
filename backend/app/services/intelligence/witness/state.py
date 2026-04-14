from typing import List, Dict, Any, TypedDict, Optional

class WitnessState(TypedDict):
    """
    🚀 [V3.5] 单文档证人状态契约
    领域：Intelligence / Witness (后端服务层)
    职责：在单文档深度审计中，追踪从意图拆解到证据质证的全过程。
    """
    # --- 核心输入 ---
    query: str                          # 原始主问题
    doc_id: str                         # 目标文档 ID
    toc: List[Dict]                     # 目标文档的逻辑脊梁 (Spine)
    
    # --- 侦察阶段 (Scouting) ---
    sub_queries: List[str]              # 拆解后的子问题任务集
    
    # --- 质证阶段 (Cross-Examination) ---
    fingerprint_pool: List[Dict]        # 全量收割回来的指纹库 (ID, Path, Tags)
    selected_ids: List[str]             # 质证员锁定的最终证据 ID
    
    # --- 合成阶段 (Deposition) ---
    pro_evidence: List[Dict]            # 最终读取的全文证据内容
    citation_ids: List[str]             # 判决书引用的分片 ID 列表
    
    # --- 状态控制 ---
    is_sufficient: bool                 # 证据是否足以回答
    final_answer: str                   # 最终生成的“单文档证词”
