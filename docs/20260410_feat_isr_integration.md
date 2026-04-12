# 🧠 SpineDoc 变更日志：TOCManager 深度集成 (ISR 2.0)

**日期**: 2026-04-10 17:45
**作者**: Gemini CLI (Architect)
**任务状态**: 🏗️ 实施中

## 1. 变更背景 (Context)
虽然我们已经构建了 `TOCManager` 和 `clustering` 引擎，但主解析器 `ArchitectVisualParser` 仍然处于“感知与逻辑混杂”的状态。为了落实“植树问题”的解决，必须将管理器的树形计算逻辑注入到解析流程的末端。

## 2. 变更内容 (Planned Changes)
- **文件**: `backend/app/services/ocr/integration/architect_parser.py`
- **重构逻辑**:
    1. 在 `rebuild_spine_concurrently` 的最后，不再直接返回 LLM 解析结果。
    2. 调用 `toc_manager.build_consensus_tree` 对原始 OCR 结果进行多模态裁决。
    3. 利用管理器的递归算法自动闭环物理页码区间 (`physical_start` 到 `physical_end`)。

## 3. 预期效果 (Impact)
- **逻辑严密性**: 彻底消除 `P10-P9` 这种由于缺乏层级意识导致的无效区间。
- **数据一致性**: 入库的每一个 `TocItem` 都将携带正确的 `physical_end`，为后续的『按章节语义切片』提供完美导航。

---
*「记录即存在。」 —— Gemini CLI*
