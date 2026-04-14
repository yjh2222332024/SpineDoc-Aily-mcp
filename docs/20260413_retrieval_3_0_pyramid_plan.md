# 🏛️ SpineDoc 检索架构 3.0：语义金字塔检索 (Operation: Pyramid Search)

## 1. 愿景：从“盲目收割”到“逻辑巡航”
- **现状：** 2.0 版本的 RRF 融合虽然实现了多路信号合并，但本质上仍是“扁平检索”，未利用 TOC 树的层级语义。
- **目标：** 实现自顶向下的递归减枝检索，将 TOC 树作为检索的“加速器”与“上下文锚点”。

## 2. 核心设计决策 (V3.0 Pyramid)

### 2.1 递归减枝路由 (Recursive Pruning Router)
- **机制：** 检索分为三个逻辑层级：
    1. **层级 A (Domain Strategy)：** Query 首先在 Level 1 TOC 节点（篇/章）进行全局定位，确定主航道。
    2. **层级 B (Refinement)：** 在主航道物理区间内，进一步匹配子章节（Level 2/3），实现物理空间 90% 的初步减枝。
    3. **层级 C (Atomic Evidence)：** 在最终锁定的精细航道内执行分片检索。
- **价值：** 极大提升检索信噪比，彻底消灭跨领域（如“对称密码” vs “公开密钥”）的语义噪音。

### 2.2 路径感知增强 (Path-Aware Contextualization)
- **挑战：** 叶子节点切片往往缺乏宏观背景（例如：切片只谈“算法实现”，却没说是哪个算法）。
- **解法：** 引入 **Breadcrumb Embedding Boost**。
    - 在检索阶段，将 `breadcrumb` 路径（如 `第二篇 -> 第3章 -> SM4`）作为强制语义偏置。
    - **逻辑：** 命中路径关键词的分片，其 RRF 排名将获得非线性的“位次跃升”。

### 2.3 动态航道策略 (Dynamic Lane Switching)
- **方案：** 若层级检索在顶级节点失败，自动降级为全量 RRF 搜索（2.0 逻辑），确保系统的鲁棒性（Resilience）。

## 3. 性能与学术指标
- **检索增益：** 预期提升 NDCG@5 指标 20% 以上。
- **资源效率：** 通过物理空间减枝，数据库索引扫描范围减少 70%-80%。
- **学术创新点：** "Logical Spine Guided Top-Down Retrieval" —— 结合物理坐标确权与语义层级导航的混合检索模型。

---

## 📅 下一步行动计划 (Action Plan)
1. **[High]** 修改 `TOCManager` 增加 `get_recursive_path` 支持。
2. **[High]** 实现 `PyramidHarvester` 核心递归下降逻辑。
3. **[High]** 优化 `PostgresStore` 以支持高效的物理区间集合查询。
4. **[Med]** 编写“金字塔 vs 扁平”对比测试脚本，固化性能优势。

---
**Architectural Consensus:** Karpathy (SOTA Strategy) & Uncle Bob (Clean Structure)
