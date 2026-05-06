# 🏛️ 联邦法庭检索系统实现日志 (2026-04-15)

## 架构决策记录

### 核心原则

1. **复用优先**：联邦法庭不重写单文档质证逻辑，而是将 `witness_graph` 作为服务调用
2. **关注点分离**：
   - `court/` - 多文档协调与裁决（行为层）
   - `thesaurus.py` - 星系映射查询（数据层，内置于 court）
3. **异步代谢**：星系合并不在写入流进行，由后台脚本定期生成 Thesaurus Map

### 目录结构

```
backend/app/services/intelligence/court/
├── __init__.py              # 包标识
├── state.py                 # 法庭状态契约 (CourtState, Testimony)
├── thesaurus.py             # 星系映射表管理器 (内部工具)
├── distributor.py           # 传唤官：根据 Thesaurus 传唤证人
├── collector.py             # 取证器：并行执行 witness_graph
├── moderator.py             # 大法官：冲突检测与裁决
└── federated_court.py       # 统一入口：编排完整流程
```

### 核心组件职责

| 组件 | 职责 | 关键方法 |
|------|------|----------|
| `ThesaurusManager` | 读取 `storage/thesaurus_map.json`，提供聚类查询 | `find_clusters_by_query(query)` |
| `Distributor` | 传唤证人文档 | `summon_witnesses(query)` → `[{'doc_id', 'galaxy_id', 'galaxy_name'}]` |
| `Collector` | 并行取证 | `collect_testimonies(docs, query)` → `[Testimony]` |
| `Moderator` | 冲突裁决 | `adjudicate(testimonies, query)` → `Verdict` |
| `FederatedCourt` | 统一入口 | `hear(query)` → 完整流程编排 |

### 数据流

```
用户查询
    │
    ▼
┌──────────────────┐
│  FederatedCourt  │
│    .hear(query)  │
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         │
┌─────────────────┐
│  Distributor    │ 1. 查询 Thesaurus → cluster_ids
│                 │ 2. 查询 DocumentGalaxyLink → summoned_docs
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Collector     │ 1. 并行调用 witness_graph (每个 doc)
│                 │ 2. 收集 testimonies
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Moderator     │ 1. 检测冲突
│                 │ 2. 裁决冲突
│                 │ 3. 生成判决书
└────────┬────────┘
         │
         ▼
    最终 verdict
```

### 测试脚本

- `tests/debug_tools/test_federated_court.py` - 全流程测试

### 下一步计划

1. **集成到 SpineEngine** - 在 `hybrid_ask` 中支持 `doc_id="all"` 时调用 FederatedCourt
2. **联网证人** - 实现 InternetWitness，调用外部 API（arXiv、Semantic Scholar）
3. **Git 备份** - 将裁决结果写入 `ChunkRevision` 表

---

**记录人**: System Agent  
**验证状态**: 已实现，待测试  
**最后更新**: 2026-04-15
