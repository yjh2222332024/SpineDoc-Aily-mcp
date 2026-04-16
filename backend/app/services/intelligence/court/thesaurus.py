"""
🗺️ Thesaurus 映射表管理器
===========================
职责：读取 storage/thesaurus_map.json，提供星系聚类查询服务。
这是联邦法庭的"地图"，用于根据查询定位相关星系集群。
"""

import json
from pathlib import Path
from typing import List, Dict, Optional, Set
from backend.app.core.config import settings


class ThesaurusManager:
    """
    🗺️ 星系同义映射表管理器

    职责：
    1. 加载 Thesaurus Map (星系聚类映射表)
    2. 根据 query 关键词匹配相关的 cluster
    3. 返回 cluster 下的所有星系信息
    """

    def __init__(self, map_path: Optional[str] = None):
        if map_path is None:
            map_path = str(Path(settings.STORAGE_ROOT) / "thesaurus_map.json")
        self.map_path = Path(map_path)
        self.thesaurus_map: Dict[str, Dict] = {}
        self._load_map()

    def _load_map(self):
        """加载 Thesaurus 映射表"""
        if self.map_path.exists():
            try:
                with open(self.map_path, "r", encoding="utf-8") as f:
                    self.thesaurus_map = json.load(f)
                print(f"🗺️ [Thesaurus] 已加载映射表：{len(self.thesaurus_map)} 个聚类")
            except Exception as e:
                print(f"⚠️ [Thesaurus] 加载异常：{e}")
                self.thesaurus_map = {}
        else:
            print(f"⚠️ [Thesaurus] 映射表不存在：{self.map_path}")

    def find_clusters_by_query(self, query: str) -> List[str]:
        """
        根据查询关键词匹配相关的 cluster

        策略：
        1. 提取 query 中的关键词（简单分词）
        2. 匹配 cluster 的 anchor_keywords
        3. 返回匹配的 cluster_id 列表
        """
        if not self.thesaurus_map:
            return []

        # 简单分词：按空格和常见分隔符拆分
        import re
        keywords = set(re.split(r'[\s,_/-]+', query.lower()))
        keywords = {kw for kw in keywords if len(kw) > 1}  # 过滤单字符

        matched_clusters = []
        for cluster_id, data in self.thesaurus_map.items():
            anchor_keywords = data.get("anchor_keywords", [])
            # 检查是否有关键词匹配
            for anchor in anchor_keywords:
                anchor_lower = anchor.lower()
                # 精确匹配或包含匹配
                if anchor_lower in keywords or any(kw in anchor_lower for kw in keywords):
                    matched_clusters.append(cluster_id)
                    break

        # 如果没有精确匹配，返回所有 cluster（兜底策略）
        if not matched_clusters:
            return list(self.thesaurus_map.keys())

        return matched_clusters

    def get_cluster_galaxies(self, cluster_id: str) -> List[Dict]:
        """获取指定 cluster 下的所有星系"""
        if cluster_id in self.thesaurus_map:
            return self.thesaurus_map[cluster_id].get("galaxies", [])
        return []

    def get_all_galaxy_ids(self, cluster_ids: List[str]) -> Set[str]:
        """获取多个 cluster 下的所有星系 ID 集合"""
        galaxy_ids = set()
        for cluster_id in cluster_ids:
            galaxies = self.get_cluster_galaxies(cluster_id)
            for galaxy in galaxies:
                galaxy_ids.add(galaxy["id"])
        return galaxy_ids

    def get_galaxy_info(self, galaxy_id: str) -> Optional[Dict]:
        """根据 galaxy_id 查找星系信息"""
        for cluster_id, data in self.thesaurus_map.items():
            for galaxy in data.get("galaxies", []):
                if galaxy["id"] == galaxy_id:
                    return {
                        "id": galaxy["id"],
                        "name": galaxy["name"],
                        "cluster_id": cluster_id
                    }
        return None
