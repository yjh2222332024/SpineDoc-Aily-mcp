import json
import os
from pathlib import Path
from typing import Dict, Set

# 🏛️ 路径锚定：使用 config 中的 STORAGE_ROOT
from backend.app.core.config import settings

class VocabularyManager:
    """"
    🏗️ 全局语义词典管家 (IDF 动态计算器)
    职责：统计词频，计算词汇的”主权权重”，识别并过滤高熵噪音。
    """
    def __init__(self, stats_path: str = None):
        if stats_path is None:
            stats_path = str(Path(settings.STORAGE_ROOT) / "11vocabulary_stats.json")
        self.stats_path = Path(stats_path)
        self.doc_count = 0
        self.word_doc_freq: Dict[str, int] = {} 
        self.co_occurrence: Dict[str, Dict[str, int]] = {} # 🚀 词对共现矩阵
        self._load_stats()

    def _load_stats(self):
        """物理加载统计数据"""
        if self.stats_path.exists():
            try:
                with open(self.stats_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.doc_count = data.get("doc_count", 0)
                    self.word_doc_freq = data.get("word_doc_freq", {})
                    self.co_occurrence = data.get("co_occurrence", {})
            except Exception as e:
                print(f"⚠️ [Vocab] 加载异常: {e}")

    def save_stats(self):
        """物理保存统计数据"""
        os.makedirs(self.stats_path.parent, exist_ok=True)
        try:
            with open(self.stats_path, "w", encoding="utf-8") as f:
                json.dump({
                    "doc_count": self.doc_count,
                    "word_doc_freq": self.word_doc_freq,
                    "co_occurrence": self.co_occurrence
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ [Vocab] 保存失败: {e}")

    def record_document(self, keywords: Set[str]):
        """
        🚀 记录新文档的词频与共现 (Hebb 学习规则)
        """
        self.doc_count += 1
        kw_list = list(keywords)
        
        # 1. 更新词频
        for word in kw_list:
            self.word_doc_freq[word] = self.word_doc_freq.get(word, 0) + 1
        
        # 2. 更新共现矩阵 (O(N^2) 但 N 很小，约 15-20)
        for i in range(len(kw_list)):
            for j in range(i + 1, len(kw_list)):
                w1, w2 = sorted([kw_list[i], kw_list[j]]) # 保持顺序一致
                if w1 not in self.co_occurrence:
                    self.co_occurrence[w1] = {}
                self.co_occurrence[w1][w2] = self.co_occurrence[w1].get(w2, 0) + 1
                
        self.save_stats()

    def is_noise(self, word: str, noise_threshold: float = 0.90) -> bool:
        """
        ⚖️ 噪音判定：如果一个词在超过 90% 的文档中出现，判定为无主权垃圾词。
        """
        if self.doc_count < 5: return False # 样本太少时不执行过滤
        
        freq = self.word_doc_freq.get(word, 0)
        ratio = freq / self.doc_count
        return ratio > noise_threshold

    def get_idf_weight(self, word: str) -> float:
        """
        📉 计算词权缩放 (IDF 权重)
        """
        import math
        freq = self.word_doc_freq.get(word, 0)
        if freq == 0: return 1.0
        # 标准 IDF 公式：log(总文档数 / (词频 + 1))
        return math.log((self.doc_count + 1) / (freq + 1)) + 1.0
