"""
🏛️ 置信度配置加载器 (Confidence Config Loader)
================================================
从 backend/storage/ 加载用户自定义配置文件，提供回退默认值。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


# 默认配置（当配置文件不存在时使用）
DEFAULT_DOMAIN_WHITELIST = {
    "authoritative_sources": [
        "arxiv.org", "ieee.org", "acm.org",
        "gov.cn", "gov", "edu.cn", "ac.cn",
    ],
    "domain_stability": {
        "arxiv.org": 0.95,
        "ieee.org": 0.95,
        "acm.org": 0.95,
        "wikipedia.org": 0.90,
        "github.com": 0.85,
        "gitlab.com": 0.85,
        "zhihu.com": 0.75,
        "juejin.cn": 0.75,
        "csdn.net": 0.65,
        "cnblogs.com": 0.65,
    }
}

DEFAULT_DOMAIN_SCORES = {
    "arxiv.org": 0.95,
    "ieee.org": 0.93,
    "acm.org": 0.92,
    "gov.cn": 0.95,
    "gov": 0.90,
    "edu.cn": 0.90,
    "wikipedia.org": 0.90,
    "github.com": 0.85,
    "zhihu.com": 0.70,
    "csdn.net": 0.60,
}

DEFAULT_DOMAIN_STATS = {
    "arxiv.org": {"h5_index": 350, "peer_reviewed": True},
    "ieee.org": {"h5_index": 280, "peer_reviewed": True},
    "acm.org": {"h5_index": 250, "peer_reviewed": True},
    "wikipedia.org": {"alexa_rank": 5, "user_generated": True},
    "github.com": {"alexa_rank": 50, "code_verifiable": True},
}

DEFAULT_CONFIDENCE_CONFIG = {
    "query_half_life": {
        "TECH_NEWS": 30,
        "RESEARCH": 180,
        "FACTUAL": 730,
    },
    "color_percentiles": {
        "GREEN": 0.65,
        "BLUE": 0.45,
        "YELLOW": 0.25,
    },
    "override_conditions": {
        "min_authoritative_sources": 2,
        "integrity_penalty": 0.5,
    }
}


class ConfidenceConfigLoader:
    """
    🏛️ 置信度配置加载器

    从 backend/storage/ 加载用户自定义配置，支持热重载。
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化配置加载器

        Args:
            storage_path: backend/storage 目录路径，默认使用项目根目录
        """
        if storage_path is None:
            # 默认路径：backend/storage
            base_dir = Path(__file__).parent.parent.parent
            storage_path = base_dir / "storage"

        self.storage_path = Path(storage_path)
        self._cache: Dict[str, Any] = {}
        self._load_all_configs()

    def _load_all_configs(self):
        """加载所有配置文件到缓存"""
        self._cache["domain_whitelist"] = self._load_json(
            "domain_whitelist.json",
            DEFAULT_DOMAIN_WHITELIST
        )
        self._cache["domain_scores"] = self._load_json(
            "domain_scores.json",
            DEFAULT_DOMAIN_SCORES
        )
        self._cache["domain_stats"] = self._load_json(
            "domain_stats.json",
            DEFAULT_DOMAIN_STATS
        )
        self._cache["confidence_config"] = self._load_json(
            "confidence_config.json",
            DEFAULT_CONFIDENCE_CONFIG
        )

    def _load_json(self, filename: str, default: Dict) -> Dict:
        """
        加载 JSON 配置文件

        Args:
            filename: 文件名
            default: 默认值（文件不存在时返回）

        Returns:
            配置字典
        """
        filepath = self.storage_path / filename

        if not filepath.exists():
            return default

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 移除 description 字段（仅用于文档）
                if isinstance(data, dict):
                    data.pop("description", None)
                return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️ 配置文件 {filename} 加载失败：{e}，使用默认值")
            return default

    def reload(self):
        """重新加载所有配置（用于热重载）"""
        self._load_all_configs()

    def get_authoritative_sources(self) -> list:
        """获取权威来源列表"""
        return self._cache["domain_whitelist"].get(
            "authoritative_sources",
            DEFAULT_DOMAIN_WHITELIST["authoritative_sources"]
        )

    def get_domain_stability(self) -> Dict[str, float]:
        """获取域名稳定性映射"""
        return self._cache["domain_whitelist"].get(
            "domain_stability",
            DEFAULT_DOMAIN_WHITELIST["domain_stability"]
        )

    def get_domain_base_scores(self) -> Dict[str, float]:
        """获取域名基础权威分"""
        return self._cache["domain_scores"].get(
            "domain_base_scores",
            DEFAULT_DOMAIN_SCORES
        )

    def get_domain_stats(self) -> Dict[str, Dict]:
        """获取域名统计信息"""
        return self._cache["domain_stats"].get(
            "domain_stats",
            DEFAULT_DOMAIN_STATS
        )

    def get_query_half_life(self) -> Dict[str, int]:
        """获取查询类型半衰期"""
        return self._cache["confidence_config"].get(
            "query_half_life",
            DEFAULT_CONFIDENCE_CONFIG["query_half_life"]
        )

    def get_color_percentiles(self) -> Dict[str, float]:
        """获取颜色分位数阈值"""
        return self._cache["confidence_config"].get(
            "color_percentiles",
            DEFAULT_CONFIDENCE_CONFIG["color_percentiles"]
        )

    def get_override_conditions(self) -> Dict[str, Any]:
        """获取本地证据推翻条件"""
        return self._cache["confidence_config"].get(
            "override_conditions",
            DEFAULT_CONFIDENCE_CONFIG["override_conditions"]
        )

    def get_min_authoritative_sources(self) -> int:
        """获取最小权威来源数"""
        return self.get_override_conditions().get(
            "min_authoritative_sources",
            DEFAULT_CONFIDENCE_CONFIG["override_conditions"]["min_authoritative_sources"]
        )

    def get_integrity_penalty(self) -> float:
        """获取完整性惩罚系数"""
        return self.get_override_conditions().get(
            "integrity_penalty",
            DEFAULT_CONFIDENCE_CONFIG["override_conditions"]["integrity_penalty"]
        )


# 全局单例
_global_loader: Optional[ConfidenceConfigLoader] = None


def get_config_loader() -> ConfidenceConfigLoader:
    """获取全局配置加载器实例"""
    global _global_loader
    if _global_loader is None:
        _global_loader = ConfidenceConfigLoader()
    return _global_loader


def reload_config():
    """重新加载配置（用于热重载）"""
    if _global_loader is not None:
        _global_loader.reload()
