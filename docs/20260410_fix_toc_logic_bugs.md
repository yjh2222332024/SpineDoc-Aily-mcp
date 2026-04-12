# 🧠 SpineDoc 故障修复日志：TOC 逻辑一致性修正

**日期**: 2026-04-10 18:10
**作者**: Gemini CLI (Architect)
**任务状态**: 🛠️ 正在修复

## 1. 发现的严重缺陷 (Critical Bugs)
- **BUG 1 (Logic)**: `manager.py` 错误使用了向后查找法而非栈式算法，导致层级跳跃时区间闭环失效。
- **BUG 2 (Physics)**: `aligner.py` 中的页码校准公式语义模糊，存在逻辑页与物理页覆盖冲突。
- **BUG 3 (Design)**: `SpineNode` 的 `physical_start` 缺失初始化路径。

## 2. 修复方案 (Corrective Actions)
- **实现真·栈式算法**: 在 `TOCManager` 中使用显式 Stack 维护当前“打开”的逻辑区间。
- **重构 Aligner 契约**: 明确 `logical_page` 为输入，`physical_start/end` 为唯一物理输出。
- **闭环验证**: 确保 `physical_end` 永远继承自父级或同级邻居。

---
*「错误的算法比没有算法更危险。」 —— Uncle Bob*
