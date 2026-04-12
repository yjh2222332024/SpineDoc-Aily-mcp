import numpy as np
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class LogicAligner:
    """
    🚀 SpineDoc 物理/逻辑页码对齐器 (V46.1)
    职责：计算逻辑页码与物理页码之间的常数偏移量。
    """
    
    @staticmethod
    def calculate_offset(toc_items: List[Dict[str, Any]]) -> int:
        """
        基于中值标定算法寻找 Offset。
        公式：物理页 = 逻辑页 + offset
        """
        logic_1_phys_candidates = []
        for item in toc_items:
            logic_p = str(item.get("page", ""))
            phys_p = item.get("physical_page")
            
            # 识别“第 1 页”标记
            if logic_p in ["1", "01", "P1"] and phys_p:
                logic_1_phys_candidates.append(int(phys_p))
        
        if not logic_1_phys_candidates:
            # 兜底：如果没找到 1，尝试推算
            return 0
            
        target_phys_page = int(np.median(logic_1_phys_candidates))
        # 🚀 关键：offset = 物理起点 - 逻辑 1 = P45 - 1 = 44
        return target_phys_page - 1

    @staticmethod
    def detect_is_scanned(toc_items: List[Dict[str, Any]]) -> bool:
        """根据数据来源判定是否为扫描件"""
        ocr_sources = [it for it in toc_items if "ocr" in str(it.get("source", "")).lower()]
        return len(ocr_sources) > len(toc_items) * 0.3
