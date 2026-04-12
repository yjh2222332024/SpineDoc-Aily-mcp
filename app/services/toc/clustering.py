import numpy as np
from typing import List, Dict, Any

class TOCClusteringEngine:
    """
    🚀 SpineDoc 物理缩进聚类引擎
    职责：基于坐标（x0）自动发现文档层级规律，消除硬编码阈值。
    """
    def __init__(self, eps: float = 25.0):
        self.eps = eps

    def get_level_map(self, x_coordinates: List[float]) -> Dict[float, int]:
        """
        一维聚类：将左边距坐标映射到层级 (1, 2, 3...)
        """
        if not x_coordinates: return {}
        
        # 1. 排序并去重
        unique_x = sorted(list(set(x_coordinates)))
        
        # 2. 简易 DBSCAN 思想：根据间距划分簇
        clusters = []
        if unique_x:
            current_cluster = [unique_x[0]]
            for x in unique_x[1:]:
                if x - current_cluster[-1] <= self.eps:
                    current_cluster.append(x)
                else:
                    clusters.append(current_cluster)
                    current_cluster = [x]
            clusters.append(current_cluster)
        
        # 3. 映射：x 越小，Level 越低 (Level 1 是最左边的)
        x_to_level = {}
        for level, cluster in enumerate(clusters, start=1):
            for x in cluster:
                x_to_level[x] = level
                
        return x_to_level

    def suggest_level(self, x0: float, x_to_level: Dict[float, int]) -> int:
        """根据 x0 坐标给出建议层级"""
        return x_to_level.get(x0, 2) # 默认为 2 级

clustering_engine = TOCClusteringEngine()
