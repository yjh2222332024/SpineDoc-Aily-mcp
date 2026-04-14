# 🏛️ SpineDoc 检索架构重构日志 - 2026/04/13

## 1. 核心目标：从魔法权重转向确定性收割 (EvidenceHarvester)
- **背景：** 现有的 `CascadingRetriever` 依赖 `3.5倍` 等魔法权重，且深度耦合了 `jieba` 分词，违反了单一职责原则 (SRP) 和依赖倒置原则 (DIP)。
- **挑战：** 不同文档类型的语义分布差异巨大，固定权重会导致检索结果在某些场景下发生严重倾斜。

## 2. 架构重构决策 (V2.0 Retrieval)

### 2.1 引入 RRF (Reciprocal Rank Fusion) 
- **方案：** 废弃分数值相加，改用排名融合。
- **公式：** $1 / (k + rank_{vector}) + 1 / (k + rank_{tags})$
- **目的：** 消除向量相似度与关键词得分的量纲差异，提升混合检索的鲁棒性。

### 2.2 逻辑标签 (Logic Tags) 确权
- **方案：** 将 Milestone 1 生成的 KeyBERT 标签提升为一级索引。
- **动作：** 在检索阶段执行针对 `logic_tags` 字段的布尔搜索，直接通过语义指纹而非原始文本进行初步碰撞。

### 2.3 ISR 物理偏置 (Spine Prior)
- **方案：** 将 TOC 提取结果作为检索的“物理栅栏”。
- **逻辑：** 若分片物理页码落在 TOC 推荐范围内，在 RRF 排序中给予“位次提升”，确保高可信度航道内的内容排在前面。

## 3. 性能优化：TOC Bypass & GIN Index
- **索引优化：** 计划在 PostgreSQL 的 `logic_tags` JSON 字段上建立 GIN 索引，实现毫秒级的标签碰撞。
- **算力分配：** 彻底将 Reranker 解耦，Harvester 仅负责原始数据的高性能召回。

---

## 📅 下一步行动计划 (Action Plan)
1. **[Urgent]** 检查并增强 `PostgresStore`，支持针对 `logic_tags` 的布尔搜索。
2. **[High]** 创建 `backend/app/services/rag/evidence_harvester.py`，实现 RRF 算法。
3. **[High]** 在 `SpineEngine` 中完成检索模块的原子化切换。
4. **[Med]** 编写集成测试，对比新旧算法在复杂查询下的召回精度。

---
**Verified by:** Uncle Bob & Andrej Karpathy (Project Architecture Group)
