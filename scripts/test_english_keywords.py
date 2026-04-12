"""
测试英文关键词提取的精度
"""

import re

# 测试文本（来自 2502.12342v1.pdf）
test_texts = [
    """
    REAL-MM-RAG: A Real-World Multi-Modal Retrieval Benchmark
    We propose a comprehensive benchmark for evaluating multi-modal 
    retrieval systems. Our approach addresses current limitations 
    in handling complex documents with tables and figures.
    """,
    
    """
    Multi-Modal Retrieval Augmented Generation (MM-RAG) systems 
    leverage visual-language models to retrieve and reason over 
    document pages containing text, tables, and images. Recent 
    advances in ColPali and other late-interaction models have 
    shown promising results in efficient retrieval.
    """,
    
    """
    Query rephrasing involves modifying the original query to create 
    variations that test the robustness of retrieval models. We 
    generate three types of rephrased queries: slight rewording, 
    significant structural changes, and comprehensive table-level 
    query comparison.
    """,
    
    """
    Our benchmark contains 120 real-world documents from diverse 
    domains including finance, healthcare, legal, and technical 
    reports. Each document is carefully annotated with relevance 
    judgments by domain experts.
    """,
]

def extract_keywords_regex(text):
    """正则提取方法"""
    # 提取 4-20 字母的单词
    english_words = re.findall(r'\b[a-zA-Z]{4,20}\b', text)
    
    # 停用词
    english_stopwords = {'the', 'and', 'for', 'with', 'from', 'this', 'that', 'have', 'has', 
                         'been', 'are', 'was', 'were', 'will', 'would', 'could', 'should',
                         'but', 'not', 'you', 'your', 'our', 'their', 'its', 'what', 'which',
                         'over', 'into', 'more', 'some', 'such', 'also', 'each', 'about'}
    
    filtered = [w for w in english_words if w.lower() not in english_stopwords]
    
    # 去重（保留顺序）
    seen = set()
    results = []
    for w in filtered:
        if w.lower() not in seen:
            results.append(w)
            seen.add(w.lower())
    
    return results[:15]

def extract_keywords_rank(text, topk=15):
    """简单词频统计方法"""
    # 提取单词
    words = re.findall(r'\b[a-zA-Z]{4,20}\b', text.lower())
    
    # 停用词
    stopwords = {'the', 'and', 'for', 'with', 'from', 'this', 'that', 'have', 'has', 
                 'been', 'are', 'was', 'were', 'will', 'would', 'could', 'should',
                 'but', 'not', 'you', 'your', 'our', 'their', 'its', 'what', 'which',
                 'over', 'into', 'more', 'some', 'such', 'also', 'each', 'about'}
    
    # 词频统计
    from collections import Counter
    filtered = [w for w in words if w not in stopwords]
    word_freq = Counter(filtered)
    
    # 取 topk
    return [w for w, _ in word_freq.most_common(topk)]

# 测试
print("=" * 80)
print("英文关键词提取方法对比测试")
print("=" * 80)

for i, text in enumerate(test_texts):
    print(f"\n📝 测试文本 {i+1}:")
    print(f"   预览：{text.strip()[:100]}...")
    
    regex_keywords = extract_keywords_regex(text)
    rank_keywords = extract_keywords_rank(text)
    
    print(f"\n   🔪 正则提取 (前 15):")
    print(f"      {', '.join(regex_keywords)}")
    
    print(f"\n   📊 词频提取 (Top 15):")
    print(f"      {', '.join(rank_keywords)}")
    
    # 人工评估
    print(f"\n   🎯 人工评估:")
    print(f"      期望关键词：benchmark, retrieval, multi-modal, query, document, ...")

print("\n" + "=" * 80)
print("总结:")
print("=" * 80)
print("""
正则提取方法:
  ✅ 优点:
    - 简单快速，无需额外依赖
    - 能提取专业术语（如 Multi-Modal, Retrieval）
    - 保留原始大小写（区分专有名词）
  
  ❌ 缺点:
    - 无法区分词性（名词/动词/形容词都提取）
    - 无法识别词组（如 "query rephrasing" 被拆成两个词）
    - 可能提取到无关词汇（如 "involves", "create"）

词频统计方法:
  ✅ 优点:
    - 能识别高频关键词
    - 自动排序，重要的在前
  
  ❌ 缺点:
    - 忽略低频但重要的术语
    - 需要足够长的文本

推荐方案:
  结合两种方法：正则提取 + 词频加权 + LLM 优化
""")
