# 变更日志 - 2026/04/13 - Witness Auditor 系统引入

## 背景
为实现“逻辑 Assassin”的闭环推理，检索层召回的结果需要经过一层“逻辑审计”。我们不再盲目相信单次搜索结果，而是由 Auditor Node 执行逻辑对齐。

## 修改范围
1. **新增 AuditorNode**:
   - 文件: `spine_cli/core/agents/witness/auditor_node.py`
   - 职责: 审计 evidence 与 TOC 承诺的对齐度。
2. **扩展 VectorStore**:
   - 文件: `backend/app/services/rag/vector_store.py`
   - 目标: 新增基于 `toc_item_id` 的按需全量读取接口 `get_chunks_by_toc_id`。
3. **工作流重排**:
   - 文件: `spine_cli/core/agents/graph.py`
   - 目标: 将 Auditor 植入 LangGraph 循环，支持 `REFILL` 分支跳转。

## 预期目标
- 逻辑完备率: 提升至 95% 以上。
- 资源浪费率: 降低 30% (通过按需补刀替代盲目全量召回)。
- 错误率: 显著降低 (Auditor 提前拦截逻辑空洞)。

## 验证策略
- 测试脚本: `tests/atoms/atoms_rag/test_witness_logic.py` (待建)
- 压力测试: 制造“缺少中间步骤”的查询，观察 Auditor 是否自动触发 `REFILL`。
