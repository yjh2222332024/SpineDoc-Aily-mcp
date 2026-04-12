# 🤖 SpineDoc Agent Fleet (V43.0 - "Metabolic Star Map" Edition)

## ⚖️ 核心哲学：逻辑代理物理 (Logic Proxy vs. Physical Reality)
针对不可编辑的 PDF（尤其是扫描件），系统不修改物理文件，而是通过 **Nexus 逻辑代理层** 实现知识的动态淘汰与重定向。

## 🛡️ 四色置信度协议 (4-Color Grounding)
- 🟢 **绿色 (SOLID)**: 证据一致，物理与网络共识。
- 🟡 **黄色 (EVOLVED)**: 知识进化。**动作：触发 Nexus Patcher 逻辑淘汰旧知识。**
- 🔴 **红色 (CONFLICT)**: 网络杂音，判定为无效纠偏，维持 PDF 权威。
- 🔵 **蓝色 (INTERNAL)**: 孤证，视为专有领域知识。

---

## 🏁 2026 路线图：取证、代谢与星图重构

### Phase 1: 实时取证与“对线”逻辑 (LogicSpy)
- **Task 1.1: 实现 WebWitness 节点**
    - **方法**: 使用 `httpx` 调用 Serper API，通过 LLM 提炼 3 个关键搜索词执行搜寻。
    - **修改代码**: `spine_cli/core/agents/federation/nodes/web_witness.py`
    - **效果**: 联邦法庭增加 `WEB_STREAM` 证据流，包含 URL、来源权重（gov/edu 判定）和脱水后的 Markdown 正文。
- **Task 1.2: 开发 SourceRanker 权重模块**
    - **方法**: 构建权威域名白名单 + 引用计数器（2+ 权威机构认证判定逻辑）。
    - **效果**: 自动判定网络证据是否具备“推翻 PDF”的资格。
- **Task 1.3: 升级 Moderator 判定逻辑**
    - **方法**: 引入“三方对冲”提示词模板，强制要求输出 `confidence_color` 和 `suggested_action`。

### Phase 2: Nexus 星图索引 (虚拟代理层)
- **Task 2.1: 定义 Nexus 结构化 Schema**
    - **修改代码**: `backend/app/core/models.py` (新增 Document.nexus_json 字段)。
    - **方法**: 包含 `spine_nodes` 状态机（Active/Deprecated/Superseded）、文档重心向量和领域标签。
    - **效果**: 为每一份长文档建立 < 100KB 的“灵魂护照”。
- **Task 2.2: 实现 NexusDistiller 压缩器**
    - **方法**: 在 Ingest 流水线末端，调用 SLM 总结逻辑脊梁并生成 Nexus JSON。
    - **修改代码**: `spine_cli/core/engine.py`

### Phase 3: 知识代谢：动态淘汰与进化 (The Metabolism)
- **Task 3.1: 实现 NexusPatcher (逻辑擦除器)**
    - **核心逻辑**: 当判定为 `YELLOW` 时，自动在 `nexus_json` 中将过期章节标记为 `DEPRECATED`，并挂载新判决的指针。
    - **修改代码**: `spine_cli/core/agents/federation/nodes/patcher.py`
    - **效果**: **实现对扫描件的“逻辑删除”**。检索时自动绕过陈旧物理页，重定向至新知识。
- **Task 3.2: 判决书归档与压缩 (Compaction)**
    - **方法**: 定期将碎片化的 `evolved_knowledge/` 判决合并为“领域黄金文档”，防止文件爆炸。
    - **效果**: 保证系统长效运行的简洁性。

### Phase 4: 检索流重构 (Galaxy Radar)
- **Task 4.1: 重构 SpineEngine.hybrid_ask 路由**
    - **逻辑**: 第一跳扫描 `Nexus JSON` -> 过滤 `DEPRECATED` 节点 -> 仅对 `ACTIVE` 节点执行向量召回。
    - **效果**: 检索速度提升 70%，且从源头上切断了“过期知识”的召回。
