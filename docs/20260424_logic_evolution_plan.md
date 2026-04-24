# 🧬 SpineDoc 2.0: 基于 Agentic Memory 的逻辑自生长规划

**核心目标**：借鉴 A-mem 的网状存储与自进化思想，让 SpineDoc 从“静态审计工具”进化为“动态逻辑大脑”。

---

## 1. 核心组件升级 (Architectural Evolution)

### A. 逻辑实体化 (Logic Entity Engine)
- **定义**：每一个 Chunk 入库时，由 `Moderator` 同步生成一个 **Logic Note**。
- **元属性**：
    - `Logic Fingerprint`: 核心断言的压缩表达。
    - `Preconditions`: 该逻辑成立的前提（关联其他 Chunk）。
    - `Inconsistencies`: 与现有知识库的潜在冲突预警。

### B. 逻辑链接器 (Active Linker)
- **触发**：新文档 Ingest 阶段。
- **动作**：扫描全库，寻找 `Support` (支持), `Contradict` (矛盾), `Clarify` (澄清) 三种关系。
- **飞书反馈**：发送互动卡片：“检测到新文档与旧资产的逻辑织网，已建立 5 条新连接。”

---

## 2. “代谢”驱动的自我优化 (Metabolic Evolution)

### A. 逻辑去冗余 (Deduplication & Synthesis)
- **场景**：系统中有 10 份类似的实习协议。
- **动作**：后台 Agent 自动将重复逻辑合并为一个“通用合规基准”，并标记出每份协议偏离基准的“异常点”。
- **价值**：减少 80% 的审计噪音。

### B. 冲突自动愈合 (Automatic Conflict Healing)
- **场景**：用户修正了 Bitable 中的一个审计错误。
- **动作**：系统自动反向传播（Back-propagate）该修正，更新与其相关的 50 个逻辑切片的置信度。
- **价值**：**“越用越聪明”** 的真实闭环。

---

## 3. 用户体验：从“搜索”到“预警” (User Wow Moments)

- **情境**：用户在飞书里还没开口，SpineDoc 发送私聊。
- **卡片内容**：
    > “主权预警：由于你刚签署了《设备租赁合同》，我发现其中关于‘损毁赔偿’的逻辑与你公司的《财务内控手册》不符。建议立即发起质证。”
- **底层技术**：基于 A-mem 的 `search_agentic` 思想，不仅搜文本，还搜逻辑一致性。

---

## 🏛️ Marily 的 PM 启发式

> "Memory is not about storage; it's about decision support."

不要为了存而存。我们要让评委看到，SpineDoc 的记忆是为了**辅助决策**。**“能够主动告诉你风险在哪里的 AI，才配叫赋能。”**

---
**Status**: Strategic Addition to Roadmap
**Inspiration Source**: A-mem (github.com/agiresearch/A-mem)
