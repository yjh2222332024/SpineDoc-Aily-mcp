# 🏛️ SpineDoc RAG 3.5: 逻辑涌现架构设计 (Operation: Emergent Spine)

> "Structure should emerge from truth, not from metadata." —— SpineDoc Architectural Manifesto

## 1. 核心哲学 (Philosophy)
- **元数据是谎言 (Metadata as a Hint)**：PDF 目录 (TOC) 往往与正文脱节，且物理偏移噪声不可控。
- **内容即真理 (Content as Truth)**：文档的正文文本流是逻辑的真实投影。通过自下而上的语义聚合，我们可以让逻辑脊梁从正文中“涌现”出来。
- **Schema 统一 (Unified Schema)**：无论文档是否有物理目录，最终入库的 `Chunk` 必须拥有完全一致的 `breadcrumb` 和 `logic_tags` 结构。

## 2. 逻辑蒸馏流水线 (The Distillery Pipeline)

### 2.1 层级 0：原子语义层 (Atomic Layer)
- **动作**：执行全量语义切片 (Semantic Splitting)，获取最原始的语义单元 `RawChunks`。
- **特点**：不预设物理边界，仅遵循文本间的“语义鸿沟”。

### 2.2 层级 1：局部话题层 (Local Consensus)
- **动作**：将物理相邻的 3-5 个切片进行“语义塌缩”。
- **模型**：利用本地极速 SLM (如 Qwen-1.8B) 生成 20 字以内的局部话题标签。
- **目的**：消除原子级的噪声，提炼局部共识。

### 2.3 层级 2：主权逻辑层 (Sovereign Logic)
- **动作**：探测局部标签间的“语义断崖”。
- **策略**：在断裂区间内调用云端高精度 LLM (DeepSeek/GLM) 执行“主权总结”。
- **产出**：生成 `SyntheticSpineNode` (虚拟章节)，它将具备与原生目录相同的 `physical_start/end` 约束。

## 3. 性能与成本纪律 (Discipline)
- **蒸馏缓存 (Distillation Cache)**：合成脊梁必须持久化在 `tocitem` 表中，标记为 `is_synthetic=True`。
- **算力分层**：
    - 局部聚合：本地低功耗模型。
    - 主权总结：云端高精度模型。
- **检索解耦**：`PyramidHarvester` 保持黑盒状态，在合成脊梁上透明巡航。

## 4. 特殊场景适配储备 (Specialized Backlog)
- **双栏学术论文**：预留 `ReadingOrderManager` 接口，计划采用“中线投影法”修复 PaddleOCR 的阅读顺序乱序问题。
- **公式与表格保护**：在蒸馏前执行“外科手术式”OCR 缝合，确保 LaTeX 语法的语义完整性。

---
**Date:** 2026/04/14
**Status:** Design Phase Approved
**Architect:** Uncle Bob & Andrej Karpathy (Project Architecture Group)
