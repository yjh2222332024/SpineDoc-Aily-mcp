"""
⚖️ SpineDoc 联邦法庭状态契约 (v2.0 证据分片版)
==============================================
定义多文档联邦检索的状态结构。
核心：证据分片是冲突分析和裁决的基本单位。
"""

from typing import List, Dict, Any, TypedDict, Optional


class EvidenceChunk(TypedDict):
    """
    证据分片：冲突分析和裁决的基本单位。
    """
    id: str
    content: str
    page_number: int
    breadcrumb: str
    logic_tags: List[str]


class EvidencePackage(TypedDict):
    """
    证据包：单个证人文档提供的全部证据。
    """
    doc_id: str
    galaxy_id: str
    galaxy_name: str
    evidence_chunks: List[EvidenceChunk]
    scout_queries: List[str]
    error: Optional[str]


class ConflictItem(TypedDict):
    """
    冲突点：大法官需要裁决的逻辑矛盾。
    """
    description: str
    packages: List[Dict[str, Any]]  # 矛盾双方的证据包引用
    severity: str  # "CRITICAL" | "MINOR"
    verdict: Optional[Dict[str, Any]]


class CourtState(TypedDict):
    """
    ⚖️ 联邦法庭状态契约 (Federated Court Contract)

    职责：管理从传唤、取证到最终审判的全生命周期。

    流水线：
    1. Summoning (传唤)  → summoned_docs
    2. Evidence Collection (取证) → evidence_packages
    3. Adjudication (审判) → conflicts + verdict
    """
    # --- 核心输入 ---
    query: str

    # --- 阶段 1: 传唤 (Summoning) ---
    summoned_docs: List[Dict[str, str]]  # [{'doc_id': '...', 'galaxy_id': '...', 'galaxy_name': '...'}]

    # --- 阶段 2: 取证 (Evidence Collection) ---
    evidence_packages: List[EvidencePackage]  # 收集所有证据包的证据分片

    # --- 阶段 3: 审判 (Adjudication) ---
    conflicts: List[ConflictItem]  # 检测到的逻辑冲突
    verdict: Optional[Dict[str, Any]]  # 最终裁决书

    # --- 状态控制 ---
    is_court_adjourned: bool  # 是否休庭
