# 20260414_galaxy_evolution_plan.md (Update: Dynamic Semantics)

## 🚀 目标：基于“赫布理论”的自演进知识图谱 (Self-Evolving Semantics)
彻底抛弃静态词库，转向基于全局统计（IDF）和关键词共现（Co-occurrence）的动态语义指纹引擎。

## 🛠️ 修改清单
1. **`backend/app/services/keyword_extractor.py`**：
   - 移除 `stopwords.txt` 静态依赖。
   - 实现全局词频统计 (IDF 预计算)，自动过滤掉在 90% 以上文档中出现的“语义垃圾”。
   - 增加词权缩放 (Weight Scaling)，提升领域核心概念权重，自动抑制通用学术用语。

2. **`backend/app/services/intelligence/galaxy/scout.py`**：
   - 增加共现矩阵记录逻辑：在文档投影时，自动记录关键词间的强关联（Edge weight）。
   - 构建动态知识图谱：利用关键词共现关系自动建立文档间的“引力桥”。

## 🎯 预期效果
- **真正的智能化**：系统能够根据你的真实入库内容，动态识别出“量化”、“密码学”、“RAG”等领域特有词汇，而无需人工干预。
- **防止碎片化**：通过共现分析，能识别出文档间的深层逻辑关联，不再因为共用“Introduction”等词而被错误聚类。
- **演进性**：随着文档入库的增加，知识图谱会自动生长，越来越贴合你个人的知识结构。

## 🛡️ 技术路径
- **IDF 过滤器**：动态计算词频倒排索引。
- **共现链路**：使用轻量级内存计数器记录指纹对，存储于 `metadata_json` 或专用关联表。
- **无监督锚点**：利用权重最高的关键词作为星系的新“标签”。
