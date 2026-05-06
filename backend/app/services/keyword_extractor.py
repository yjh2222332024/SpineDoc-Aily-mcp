"""
SpineDoc 语义指纹机 (V1.2 - Stopwords Guard Edition)
==================================================
架构使命：
1. 语义净土：自动加载 storage/stopwords.txt，物理隔绝高熵噪音。
2. 双重过滤：结合 KeyBERT 内部过滤与后置物理清理，确保关键词质量。
3. 极致轻量：保持 MiniLM 的高性能，确保在轻薄本上秒级响应。
"""

import os
import asyncio
import logging
from typing import List, Optional, Set, Dict, Any
from backend.app.core.config import settings
from pathlib import Path
from backend.app.services.ingestion.llm_service import llm_service

class KeywordExtractor:
    """
    语义关键词提取单例服务 (V3.0 - Cloud-Native Edition)
    """
    _instance = None
    
    #  硬性纪律：学术脚手架词汇 (Boilerplate)
    ACADEMIC_BOILERPLATE = {
        "training details", "data processing", "experimental results", "proposed method",
        "performance evaluation", "future work", "related work", "implementation details",
        "conclusion", "methodology", "algorithm module", "framework data", "module trading",
        "datasets construction", "processing module", "visualization algorithm", "metrics training",
        "evaluation metrics", "training process", "data collection", "datasets evaluation",
        "module experience", "experience datasets", "preliminaries", "setup", "introduction",
        "background", "abstract", "summary", "overview", "discussion", "limitations",
        "conclution", "results", "analysis", "experiments", "experimentation", "method",
        "references", "bibliography", "appendices", "appendix", "acknowledgments",
        "基本概念", "研究 背景", "实验 结果", "结论 展望", "参考文献", "系统 架构", "实现 细节",
        "习题 解答", "阅读 习题", "快速 入门", "核心 概念", "构建 评估", "模型 评估"
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KeywordExtractor, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # 1. 加载全局停用词表
        stopwords_path = Path(__file__).parent.parent / "core" / "stopwords.txt"
        self.stopwords = set()
        if stopwords_path.exists():
            with open(stopwords_path, "r", encoding="utf-8") as f:
                self.stopwords = {line.strip() for line in f if line.strip()}

    async def extract_keywords(self, text: str, top_n: int = 10) -> List[str]:
        """
         [V3.0] 云端确权提取：使用 LLM 替代本地 KeyBERT
        """
        if not text:
            return []

        prompt = f"""请作为首席架构师，从以下文本中提取最能代表其核心语义的 {top_n} 个关键词或短语。
要求：
1. 关键词必须具有高度的逻辑辨识度。
2. 排除掉诸如“介绍”、“背景”、“结果”等无意义的学术废话。
3. 严格输出 JSON 格式：{{"keywords": ["k1", "k2", ...]}}

【待提取文本】：
{text[:2000]}
"""
        try:
            resp = await llm_service.chat_completion(prompt, response_format="json")
            keywords = resp.get("keywords", [])
            
            #  物理过滤：应用本地停用词与黑名单
            clean_keywords = []
            for kw in keywords:
                kw_clean = kw.strip().lower()
                if kw_clean in self.ACADEMIC_BOILERPLATE: continue
                if any(p in self.stopwords for p in kw_clean.split()): continue
                if len(kw_clean) <= 1: continue
                clean_keywords.append(kw_clean)
                
            return clean_keywords[:top_n]
        except Exception as e:
            print(f" [Keywords] 云端提取失败: {e}")
            return []

def get_keyword_extractor():
    return KeywordExtractor()
