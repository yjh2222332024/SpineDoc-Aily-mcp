import math
import logging
from typing import Any, Dict, Optional
from datetime import datetime
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class AuthorityModel:
    """
    AuthorityModel: Pure logic for domain authority scoring.
    """
    def __init__(self, base_scores: Dict[str, float], max_h5: int = 500):
        self.base_scores = base_scores
        self.max_h5 = max_h5

    def get_score(self, domain: str, stats: Optional[Any] = None) -> float:
        # 1. 精确与模糊匹配
        for pattern, score in self.base_scores.items():
            if domain == pattern or domain.endswith("." + pattern):
                return score
        
        # 2. 基于统计的动态计算
        if stats:
            return self._compute_from_stats(stats)
            
        return 0.50 # 保守估计

    def _compute_from_stats(self, stats) -> float:
        if stats.h5_index:
            base = math.log(stats.h5_index + 1) / math.log(self.max_h5 + 1)
            if stats.peer_reviewed:
                return min(1.0, base * settings.COURT_AUTHORITY_PEER_REVIEW_BONUS)
            return base
            
        if stats.alexa_rank:
            base = math.log(1 / stats.alexa_rank) / math.log(1 / 5)
            if stats.user_generated:
                return max(0.3, base * settings.COURT_AUTHORITY_USER_GENERATED_PENALTY)
            return base
        return 0.50

class DecayModel:
    """
    DecayModel: Pure logic for time-based weight decay.
    """
    def __init__(self, half_life_config: Dict[str, int]):
        self.half_life_config = half_life_config

    def calculate_decay(self, publish_date_str: Optional[str], query_type: str) -> float:
        if not publish_date_str:
            return 0.8 # 缺失日期，给予惩罚
            
        try:
            publish_date = datetime.fromisoformat(publish_date_str.split('T')[0])
            days_old = (datetime.now() - publish_date).days
            days_old = max(0, days_old)
            
            half_life = self.half_life_config.get(query_type, 365)
            lam = math.log(2) / half_life
            return math.exp(-lam * days_old)
        except Exception:
            return 0.7
