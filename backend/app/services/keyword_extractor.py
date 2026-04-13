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

class KeywordExtractor:
    """
    语义关键词提取单例服务 (带黑名单防护)
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KeywordExtractor, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # 1. 核心模型加载
        model_name = "paraphrase-multilingual-MiniLM-L12-v2"
        # 🏛️ 顶级架构师：强制锁定模型缓存路径
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

        # 2. 🛡️ 建立防火墙：加载停用词黑名单
        self.stop_words: Set[str] = set()
        self._load_stopwords()

    def _load_stopwords(self):
        """加载物理停用词文件"""
        # 🏛️ 寻找路径：支持相对路径与绝对路径
        possible_paths = [
            Path("storage/stopwords.txt"),
            Path(__file__).resolve().parent.parent.parent / "storage" / "stopwords.txt"
        ]
        
        for path in possible_paths:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        for line in f:
                            word = line.strip().lower()
                            if word and not word.startswith("#"):
                                self.stop_words.add(word)
                    print(f"🛡️ [Keywords] 已加载 {len(self.stop_words)} 个语义黑名单词项")
                    return
                except Exception as e:
                    print(f"⚠️ [Keywords] 停用词加载异常: {e}")
        
        print("⚠️ [Keywords] 未找到 storage/stopwords.txt，运行在无码模式。")

    def extract_keywords(self, text: str, top_n: int = 20) -> List[str]:
        """
        从文本中提取语义标签 (带后置物理净化)
        """
        if not text or not self.model:
            return []

        try:
            # 🏛️ 专业的预处理：针对中文进行分词，提升 KeyBERT 候选词质量
            seg_list = jieba.cut(text)
            segmented_text = " ".join(seg_list)

            # 提取关键词
            # 🏛️ 我们先让 KeyBERT 粗筛，然后再进行精确的物理过滤
            keywords_with_scores = self.model.extract_keywords(
                segmented_text, 
                keyphrase_ngram_range=(1, 2), 
                use_mmr=True, 
                diversity=0.7, 
                top_n=top_n + 10 # 多拿几个，为后置过滤留空间
            )
            
            # 🏛️ 后置净化：物理剔除残留噪音及单字噪音
            cleaned_keywords = []
            for kw, score in keywords_with_scores:
                kw_clean = kw.strip().lower()
                
                # 过滤逻辑：
                # 1. 词长必须 > 1 (除非是 Sha 等硬特征)
                # 2. 不在我们的物理黑名单中
                # 3. 排除纯数字或极其简短的干扰
                if (len(kw_clean) > 1 or kw_clean.isdigit()) and kw_clean not in self.stop_words:
                    cleaned_keywords.append(kw_clean)
                
                if len(cleaned_keywords) >= top_n:
                    break
            
            return cleaned_keywords
        except Exception as e:
            print(f"⚠️ [Keywords] 提取异常: {e}")
            return []

# 导出单例获取函数
def get_keyword_extractor():
    return KeywordExtractor()
