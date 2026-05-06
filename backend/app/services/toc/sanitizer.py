"""
SpineDoc 标题清洗器 (TitleSanitizer) - 2026/04/11 混合动力版
============================================================
职责：集成向量相似度、编辑距离、子串包含、层级权重四重防御，彻底消灭 OCR 标题重影。
"""
from typing import List
import numpy as np
import logging
import re
from .base import SpineNode

logger = logging.getLogger(__name__)

class VectorizedTitleSanitizer:
    def __init__(self, vector_threshold: float = 0.88, edit_threshold: float = 0.85):
        self.vector_threshold = vector_threshold
        self.edit_threshold = edit_threshold
        self.model = None
        
    def _get_model(self):
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.model = SentenceTransformer("BAAI/bge-small-zh-v1.5", device="cpu")
                logger.info("🧠 TitleSanitizer: BGE-Small (CPU) Ready.")
            except Exception as e:
                logger.error(f" Failed to load model: {e}")
        return self.model

    def _levenshtein_sim(self, s1: str, s2: str) -> float:
        """简单的模糊匹配度 (Software 1.0 降维打击)"""
        # 移除数字和符号再比对
        s1_clean = re.sub(r'[^\u4e00-\u9fa5]', '', s1)
        s2_clean = re.sub(r'[^\u4e00-\u9fa5]', '', s2)
        if not s1_clean or not s2_clean: return 0.0
        
        # 计算子串重合度
        if s1_clean in s2_clean or s2_clean in s1_clean:
            return 1.0
            
        from difflib import SequenceMatcher
        return SequenceMatcher(None, s1_clean, s2_clean).ratio()

    def sanitize(self, nodes: List[SpineNode]) -> List[SpineNode]:
        """
        核心逻辑：多维去重 + 排序。
        """
        if not nodes: return []
        
        # 1. 首先确保全局按逻辑页码和原始顺序排序，消除并行 OCR 的乱序初影
        nodes.sort(key=lambda x: (x.logical_page, x.index))
        
        model = self._get_model()
        from collections import defaultdict
        page_map = defaultdict(list)
        for n in nodes:
            page_map[n.logical_page].append(n)

        final_nodes = []
        
        for page, group in page_map.items():
            if len(group) <= 1:
                final_nodes.extend(group)
                continue
            
            # 向量化
            titles = [n.title for n in group]
            embeddings = model.encode(titles, normalize_embeddings=True) if model else None
            
            to_skip = set()
            page_final = []
            
            for i in range(len(group)):
                if i in to_skip: continue
                
                best_node = group[i]
                page_final.append(best_node)
                
                for j in range(i + 1, len(group)):
                    if j in to_skip: continue
                    
                    # 策略 A：向量相似度 (语义)
                    v_sim = np.dot(embeddings[i], embeddings[j]) if embeddings is not None else 0.0
                    
                    # 策略 B：字面相似度 (针对“侧侧侧”这种叠词幻觉)
                    l_sim = self._levenshtein_sim(group[i].title, group[j].title)
                    
                    if v_sim >= self.vector_threshold or l_sim >= self.edit_threshold:
                        logger.info(f" [Sanitizer] 合并重影: '{group[j].title}' (L{group[j].level}) -> '{group[i].title}' (L{group[i].level}) | V:{v_sim:.2f} L:{l_sim:.2f}")
                        to_skip.add(j)
                        
                        # 权重策略：保留层级最浅的（通常是更准确的章节定义）
                        if group[j].level < best_node.level:
                            best_node.level = group[j].level
                            best_node.title = group[j].title # 更新为更上层的标题名
            
            final_nodes.extend(page_final)
            
        # 2. 最终重排序：确保 Index 也是连续且单调递增的
        final_nodes.sort(key=lambda x: (x.logical_page, x.physical_start))
        for i, n in enumerate(final_nodes):
            n.index = i
            
        return final_nodes

title_sanitizer = VectorizedTitleSanitizer()
