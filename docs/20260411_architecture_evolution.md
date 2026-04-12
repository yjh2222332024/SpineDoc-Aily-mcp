# 🏛️ SpineDoc 架构演化宪章 - 2026/04/11 (Revised)

> "不仅要搜得准，更要拆得深。好的检索源于对问题的深刻解构。" —— SpineDoc 架构团队

## 一、 核心原则

1. **机制与策略分离 (Mechanism vs. Policy)：**
   - **机制层 (EvidenceHarvester)：** 确定性的、Hybrid + RRF 混合检索。
   - **策略层 (Navigator)：** 具备多维解构能力的智能大脑。

2. **意图解构导向 (Deconstruction-Led)：**
   - 复杂问题不再直接检索，必须经过 **Sub-Query Decomposition**。

---

## 二、 核心组件规范

### 2.1 EvidenceHarvester (机械收割机)
- **职责：** 卑微的机械取菜员。
- **算法：** BM25 + Vector + **RRF 排名融合**。
- **性能红线：** < 100ms。

### 2.2 Navigator 3.0 (多维推理引擎)
- **Step 1: Query Deconstructor (SLM)：** 
  - 将根问题解构为多个正交子问题（如：原材料、工艺、厨具）。
  - 利用子问题并行触发 Harvester，实现“多维坐标撞击”。
- **Step 2: Structural Anchor：** 
  - 强制解析 ISR/TOC 定位正文起始页，取代 `page > 25`。
- **Step 3: Multi-hop Investigator：** 
  - 根据子问题的反馈缺失，动态重写查询进行深挖。
- **Step 4: Verdict Editor：** 
  - 级联筛选后的 Top-3 核心证据回溯 Full-page OCR，合成最终判决。

### 2.3 星图知识体系 (Star-Map)
- **定位：** 全局章节语义索引，辅助 Navigator 进行跨文档定位。

---

## 三、 实施 Roadmap (2026 Q2)

1. **Phase 1 (The Foundation):** 实现 `EvidenceHarvester` (RRF + Hybrid)。
2. **Phase 2 (The Brain):** 实现 `Navigator` 子问题拆解逻辑与 ISR 锚点定位。
3. **Phase 3 (The Court):** 重构 `Federated Court` 实现隔离辩论与证据对线。

---
*记录人：Andrej Karpathy & Uncle Bob & 学生(匿名)*
