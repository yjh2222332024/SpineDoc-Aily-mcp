# SpineDoc 量化指标

> 基于当前系统实测数据（doubao-2.0 via 火山引擎，Bitable 持久层），
> 覆盖性能、精度、规模、可用性四个维度。

---

## 一、性能指标 (Performance)：LogicCourt 图引擎各阶段响应时延实测

### 1.1 端到端响应时延：单文档 vs 跨文档双路径耗时对比

| 场景 | 优化前 | 优化后 | 加速比 | 优化措施 |
|------|--------|--------|--------|---------|
| 单文档质证 | 170s | **90s** | 1.9x | 跳过 PLAN、移除 AnswerBuilder 二次 LLM 调用、EVOLVE 异步 dispatch |
| 跨文档质证 | — | **170s** | — | 全链路 5 阶段，PLAN 拆分 + 多星系并行 HARVEST |

### 1.2 阶段耗时分布：phase_log 实测 5 阶段 waterfall（单文档断点时序）

基于 phase_log 实录（测试 query: "这个文档的核心架构是什么"，doc recvis00...）：

| 阶段 | 耗时 | 占比 | 说明 |
|------|------|------|------|
| HARVEST | 29s | 32% | SovereignSentry 本地检索 + Zhipu Reranker + WitnessExpert 联网检索 + 逻辑脱水 |
| AUDIT | ~0s | <1% | 冲突检测纯计算，无 LLM 调用 |
| SYNTHESIZE | 60s | 67% | 单次 doubao-2.0 LLM 调用，生成 internal_consensus + assistant_answer |
| EVOLVE | async | 0% | 异步 dispatch，不阻塞主流程 |
| **合计** | **90s** | 100% | 其中 LLM 耗时约 60s（67%），为主要瓶颈 |

### 1.3 LLM 推理开销：doubao-2.0 单次调用 60s 占全链路 67%

| 指标 | 值 |
|------|-----|
| 模型 | doubao-2.0 (ark.cn-beijing.volces.com) |
| 单次调用平均耗时 | ~60s |
| 每次质证调用次数 | 1（SYNTHESIZE 阶段） |
| 优化前调用次数 | 2（SYNTHESIZE + AnswerBuilder） |
| 优化节省 | -50s / 次 |

### 1.4 子系统检索速度：Bitable / Reranker / WebSearch 四阶段逐级分解

| 子系统 | 平均耗时 | 说明 |
|--------|---------|------|
| Bitable chunks 搜索 (POST /records/search) | ~3s | 按文档关联字段过滤，单表检索 |
| Zhipu Reranker 重排 | ~5s | 对候选 chunks 进行语义重排序 |
| 飞书 Web Search (config API) | ~15s | 联网搜索 + 结果解析 |
| WitnessExpert 逻辑脱水 | ~5s | 对联网结果进行主张提取 |

### 1.5 系统吞吐量：质证 / 导入 / 查询三场景并发能力实测

| 场景 | 实测值 |
|------|--------|
| 单文档质证并发 | 1 req / 90s（串行，LLM 为瓶颈） |
| 文档导入（PDF < 100页） | ~30s / 份 |
| 文档导入（PDF 100-500页） | ~120s / 份 |
| 文档列表查询 | <1s |

---

## 二、精度指标 (Accuracy)：四色置信度语义体系与证据溯源质量

### 2.1 置信度体系

| 颜色 | 置信度区间 | 含义 | 触发条件 |
|------|-----------|------|---------|
| 🟢 GREEN | ≥ 0.80 | 高置信度，证据充分 | 本地证据 + 联网证据交叉验证一致 |
| 🟡 YELLOW | 0.50 - 0.79 | 中等置信度，存在不确定性 | 单来源证据、或本地与联网存在轻微矛盾 |
| 🔴 RED | < 0.50 | 低置信度，证据不足 | 证据不足、或检测到重大逻辑冲突 |

### 2.2 置信度计算模型

```
confidence = avg(claim_weights.values())

claim_weights = f(source_authority, evidence_count, conflict_resolution)
  - source_authority: 本地=0.80(base), 联网=0.70(base)
  - StabilityAnchor: 0.80 阈值抑制时间衰减
  - conflict_resolution: 冲突解决后权重恢复
```

### 2.3 实测精度

| 场景 | 置信度 | 证据数 | 冲突数 |
|------|--------|--------|--------|
| 单文档，单来源，无冲突 | 0.80 - 1.00 | 5-10 条 | 0 |
| 单文档，含联网验证 | 0.90 - 1.00 | 7-15 条 | 0-1 |
| 跨文档，多来源一致 | 0.85 - 1.00 | 10-30 条 | 0-2 |
| 跨文档，存在矛盾 | 0.40 - 0.70 | 10-20 条 | 1-5 |

### 2.4 证据溯源质量

| 指标 | 值 |
|------|-----|
| 证据字段完整率 | 100%（id, content, claims, color, confidence, source_name, page_number, breadcrumb, origin） |
| 来源去重 | `seen_ids` set 级去重 |
| 证据裁剪 | AUDIT 阶段物理脱水，保留关键字段 |
| 颜色归一化 | `ConfidenceColor.YELLOW` → `YELLOW` 全链路一致 |

---

## 三、规模指标 (Scale)：Bitable 持久层容量与 LogicCourt 图引擎处理上限

### 3.1 文档处理能力

| 维度 | 指标 |
|------|------|
| 单文档最大页数 | 未压测上限（实测 200+ 页 PDF 正常） |
| 知识库文档数 | 无限制（Bitable 表容量上限） |
| 单次质证证据池上限 | 无硬限制，AUDIT 阶段两两比对复杂度 O(n²)，n < 50 时性能可接受 |
| 迭代上限 | `max_iteration = 10`（含补充侦查重入） |
| 超时熔断 | `max_duration = 600s` |

### 3.2 Bitable 持久层规模

| 维度 | 指标 |
|------|------|
| documents 表记录 | 无限制 |
| chunks 表记录 | 无限制 |
| 单文档平均 chunk 数 | ~20-50 / 100 页 |
| 检索响应 | ~3s / 次 POST records/search |

### 3.3 MCP 接口规模

| 维度 | 指标 |
|------|------|
| 工具数 | 4（ingest, ask, ask_all, list_docs） |
| 单次输出 JSON 大小 | ~5-50 KB（含 evidence_trace） |
| 并发能力 | 受 LLM 串行限制，MCP 层无瓶颈 |

---

## 四、可用性指标 (Reliability)

### 4.1 容错机制

| 机制 | 触发条件 | 行为 |
|------|---------|------|
| `_force_finalize()` | 超时 600s 或 iteration ≥ 10 | 返回当前 state，final_answer="系统超时未能完成完整推理" |
| 补充侦查重入保护 | re_harvest_count 递增 | 上限保护，防止无限 HARVEST↔AUDIT 循环 |
| MCP 异常捕获 | 引擎内部任何 Exception | 返回 `{status:"error", message:"..."}`，服务不崩溃 |
| 幂等导入 | 重复导入同一文件 | 返回已有 doc_id，不创建重复记录 |
| 卡片渲染回退 | interactive_card 不存在 | `LarkCliReporter` 自动调用 `build_result_card()` 回退构建 |

### 4.2 可观测性

| 维度 | 实现 |
|------|------|
| 阶段耗时 | phase_log 记录每阶段 `duration_s` |
| 证据数量 | phase_log HARVEST 阶段 `detail: "N 条证据"` |
| 冲突数量 | phase_log AUDIT 阶段 `detail: "N 处冲突"` |
| 置信度 | final_results[0].result_metadata.confidence |
| 错误追踪 | MCP ctx.log_error() / print / logger.error |

### 4.3 系统依赖

| 依赖 | 故障影响 | 降级策略 |
|------|---------|---------|
| 火山引擎 LLM | 质证不可用 | 无降级（核心依赖） |
| 飞书 Bitable | 检索/导入不可用 | 无降级（核心依赖） |
| 飞书 Web Search | 联网检索不可用 | 仅本地检索，置信度上限 0.80 |
| lark-cli | 飞书消息推送失败 | 无降级（纯输出通道） |
| Zhipu Reranker | 重排不可用 | 直接使用 Bitable 原始排序 |

---

## 五、与同类系统对比

| 指标 | SpineDoc | GraphRAG | LightRAG | 说明 |
|------|----------|----------|----------|------|
| 端到端时延 | 90s | >500ms | >100ms | SpineDoc 含 LLM 推理时间，后者仅为检索时延 |
| 多智能体协作 | ✅ 5 阶段图引擎 | ❌ | ❌ | 仅 SpineDoc 具备多智能体辩论能力 |
| 证据溯源 | ✅ 结构化溯源链 | ❌ | ❌ | 含页码、来源、置信度、颜色标记 |
| 联网验证 | ✅ WitnessExpert | ❌ | ❌ | 自动联网交叉验证 |
| 知识自演化 | ✅ EVOLVE 异步回填 | ❌ | ❌ | 闭环持续进化 |
| 飞书生态集成 | ✅ 互动卡片 + Aily | ❌ | ❌ | 原生深度集成 |
| 置信度颜色体系 | ✅ 4 色语义 | ❌ | ❌ | 可视化置信度 |
| phase_log 白盒化 | ✅ 每阶段结构化输出 | ❌ | ❌ | 过程可审计 |

---

## 六、已知瓶颈与优化方向

| 瓶颈 | 当前值 | 优化方向 | 预期提升 |
|------|--------|---------|---------|
| LLM 单次调用 60s | 占总耗时 67% | 换模型（doubao → 更快模型） | 10-30s |
| SYNTHESIZE 串行 | 单次调用等待 60s | 流式输出 + 部分结果提前渲染 | 感知提升 50% |
| 证据池两两比对 O(n²) | n < 50 时可接受 | 引入向量聚类预筛选 | 支持 n > 100 |
| Bitable API 限频 | 未压测 | 本地缓存 + 批量请求 | — |

---

> 最后更新：2026-05-04
> 基于 doubao-2.0，火山引擎 ark.cn-beijing.volces.com，飞书 Bitable 持久层
