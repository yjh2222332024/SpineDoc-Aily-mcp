"""
Copyright (c) 2026 Yan Junhao (严俊皓). All rights reserved.
Project: SpineDoc - Advanced Structural RAG
Author: Yan Junhao (严俊皓)
License: Private / Proprietary (Unauthorized copying is strictly prohibited)
"""
from typing import List, Dict, Any
from app.schemas.document import DocumentType

class TOCValidator:
    """
    TOC Rule Engine: Implements production-grade logic.
    """
    @staticmethod
    def check_monotonicity(toc: List[Dict[str, Any]]) -> float:
        if not toc: return 0.0
        violations = 0
        last_page = -1
        for item in toc:
            current_page = item.get("page", 0)
            if current_page < last_page:
                violations += 1
            last_page = current_page
        return 0.8 if violations > 0 else 0.0

    @staticmethod
    def calculate_adaptive_density(toc: List[Dict[str, Any]], total_pages: int, doc_type: DocumentType) -> float:
        if total_pages <= 0: return 1.0
        expected_ratio = 0.1 if doc_type == DocumentType.NATIVE else 0.02
        actual_ratio = len(toc) / total_pages
        return 0.5 if actual_ratio < expected_ratio else 0.0

    @staticmethod
    def quantify_conflicts(conflict_report: List[Dict[str, Any]]) -> float:
        score_penalty = 0.0
        for conflict in conflict_report:
            msg = conflict.get("msg", "").lower()
            if "level" in msg or "hierarchy" in msg:
                score_penalty += 0.3
            elif "page" in msg or "not found" in msg:
                score_penalty += 0.5
        return min(0.9, score_penalty)

    MAX_PAGES_LIMIT = 5000
    MAX_DEPTH_LIMIT = 8
    MAX_ITEMS_LIMIT = 1000

    @classmethod
    def evaluate_quality(cls, toc: List[Dict[str, Any]], total_pages: int, doc_type: DocumentType, conflicts: List[Dict[str, Any]]) -> float:
        if total_pages > cls.MAX_PAGES_LIMIT or len(toc) > cls.MAX_ITEMS_LIMIT:
            return 0.0
        max_depth = 0
        if toc:
            max_depth = max(item.get("level", 1) for item in toc)
        if max_depth > cls.MAX_DEPTH_LIMIT:
            return 0.0
        base_score = 1.0
        base_score -= cls.check_monotonicity(toc)
        base_score -= cls.calculate_adaptive_density(toc, total_pages, doc_type)
        base_score -= cls.quantify_conflicts(conflicts)
        return max(0.1, base_score)
