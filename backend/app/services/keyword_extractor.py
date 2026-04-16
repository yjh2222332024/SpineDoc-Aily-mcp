"""
SpineDoc 语义指纹机 (V1.2 - Stopwords Guard Edition)
==================================================
架构使命：
1. 语义净土：自动加载 storage/stopwords.txt，物理隔绝高熵噪音。
2. 双重过滤：结合 KeyBERT 内部过滤与后置物理清理，确保关键词质量。
3. 极致轻量：保持 MiniLM 的高性能，确保在轻薄本上秒级响应。
"""

import os
import jieba
from typing import List, Optional, Set
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from backend.app.core.config import settings
from pathlib import Path

from backend.app.services.intelligence.galaxy.utils.vocabulary import VocabularyManager

class KeywordExtractor:
    """
    语义关键词提取单例服务 (V2.2 - Zero Tolerance Edition)
    """
    _instance = None
    
    # 🏛️ 硬性纪律：学术脚手架词汇 (Boilerplate)
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
    
    # 🏛️ 语义弱词：如果 2-gram 中两个词都是弱词，直接踢出
    WEAK_WORDS = {
        "details", "processing", "module", "framework", "results", "analysis", 
        "evaluation", "datasets", "approach", "method", "proposed", "paper",
        "study", "research", "training", "testing", "metrics", "experiment",
        "system", "model", "performance", "effective", "efficient", "accuracy",
        "construction", "implementation", "design", "architecture", "overview",
        "process", "documents", "data", "information", "knowledge", "structure",
        "研究", "分析", "实验", "测试", "评估", "实现", "构建", "设计", "方法",
        "论文", "系统", "模型", "框架", "结构", "细节", "过程", "结果", "对比",
        "准备", "应用", "展望", "总结", "基本", "概念", "理论", "基础", "概论"
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KeywordExtractor, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # 1. 加载全局停用词表 (从 core/ 配置目录读取)
        stopwords_path = Path(__file__).parent.parent / "core" / "stopwords.txt"
        self.stopwords = set()
        if stopwords_path.exists():
            with open(stopwords_path, "r", encoding="utf-8") as f:
                self.stopwords = {line.strip() for line in f if line.strip()}
        print(f"✅ [Keywords] 停用词表已加载：{len(self.stopwords)} 个条目")

        # 2. 模型加载
        model_name = "paraphrase-multilingual-MiniLM-L12-v2"
        cache_dir = str(Path(settings.CACHE_DIR) / "sentence-transformers")
        os.makedirs(cache_dir, exist_ok=True)
        os.environ["SENTENCE_TRANSFORMERS_HOME"] = cache_dir
        
        print(f"🚀 [Keywords] 正在加载语义引擎 {model_name}...")
        
        try:
            st_model = SentenceTransformer(model_name)
            self.model = KeyBERT(model=st_model)
            print("✅ [Keywords] 语义指纹机核心已就绪")
        except Exception as e:
            print(f"❌ [Keywords] 引擎加载失败: {e}")
            self.model = None

        self.vocab = VocabularyManager()

    def extract_keywords(self, text: str, top_n: int = 20) -> List[str]:
        """
        从文本中提取语义标签 (带双弱判定与多重物理防御)
        """
        if not text or not self.model:
            return []

        try:
            seg_list = jieba.cut(text)
            segmented_text = " ".join(seg_list)

            candidates = self.model.extract_keywords(
                segmented_text, 
                keyphrase_ngram_range=(1, 2), 
                use_mmr=True, 
                diversity=0.7, 
                top_n=top_n + 50 
            )
            
            weighted_candidates = []
            for kw, score in candidates:
                kw_clean = kw.strip().lower()
                
                # 🛡️ 拦截 1：硬性黑名单拦截 + 停用词表拦截
                # 职业化升级：如果 2-gram 中包含任何一个噪音词，直接物理剔除
                parts = kw_clean.split()
                if any(p in self.ACADEMIC_BOILERPLATE for p in parts):
                    continue
                if any(p in self.stopwords for p in parts):
                    continue
                
                # 🛡️ 拦截 2：全词匹配黑名单 (冗余保护)
                if kw_clean in self.ACADEMIC_BOILERPLATE:
                    continue
                
                # 🛡️ 拦截 3：双弱判定 (Double-Weak Veto)
                if len(parts) == 2:
                    if parts[0] in self.WEAK_WORDS and parts[1] in self.WEAK_WORDS:
                        continue 
                elif len(parts) == 1:
                    if parts[0] in self.WEAK_WORDS:
                        continue 

                # 🛡️ 拦截 4：词长与数字
                if len(kw_clean) <= 1 and not kw_clean.isdigit():
                    continue

                # 🛡️ 拦截 5：动态 IDF 噪音过滤
                if self.vocab.is_noise(kw_clean, noise_threshold=0.6):
                    continue
                
                # 🚀 归档：加权计算
                idf_weight = self.vocab.get_idf_weight(kw_clean)
                final_score = score * idf_weight
                weighted_candidates.append((kw_clean, final_score))
            
            # 🏛️ 二次排序
            weighted_candidates.sort(key=lambda x: x[1], reverse=True)
            return [kw for kw, score in weighted_candidates[:top_n]]
        except Exception as e:
            print(f"⚠️ [Keywords] 提取异常: {e}")
            return []




# 导出单例获取函数
def get_keyword_extractor():
    return KeywordExtractor()
