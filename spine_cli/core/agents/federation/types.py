from dataclasses import dataclass, field
from typing import List, Optional, Literal, Dict
from enum import Enum

class ClaimType(Enum):
    FACT = "fact"
    OPINION = "opinion"
    CONFLICT = "conflict"

@dataclass
class AtomicClaim:
    """原子论点：不可分割的事实单元"""
    content: str
    page: int
    witness_id: str
    claim_type: ClaimType = ClaimType.FACT
    confidence: float = 1.0
    raw_text: str = ""

@dataclass
class CollisionPoint:
    """冲突点：辩论的核心争议"""
    collision_type: Literal["PAGE_CONFLICT", "VALUE_CONFLICT", "LOGIC_GAP"]
    description: str
    involved_witnesses: List[str]
    evidence_claims: List[AtomicClaim]
    severity: float = 1.0  # 1.0 为致命冲突

@dataclass
class ModeratorDecision:
    """主理人决策包"""
    status: Literal["CONSENSUS", "CONFLICT", "INSUFFICIENT"]
    collisions: List[CollisionPoint]
    next_step: Literal["REFINE", "DONE", "ERROR"]
    refine_questions: List[Dict[str, str]] # {"target": "DOC_1", "question": "..."}
