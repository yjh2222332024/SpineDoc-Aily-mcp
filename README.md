# 🛡️ SpineDoc (阅脊)

**逻辑刺客级文档审计引擎** - 专为审计合同、论文、法律文书等长文档设计

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **"不要只是与 PDF 聊天，去重构它们的逻辑。"**

---

## 📖 什么是 SpineDoc？

SpineDoc 是一个面向**长文档审计**的智能知识引擎。它不仅能回答"文档说了什么"，更能揭示"逻辑是否自洽"、"证据是否充分"、"是否有隐藏矛盾"。

### 核心能力

| 能力 | 说明 |
|------|------|
| 🦴 **逻辑脊梁提取** | 自动识别文档的 implicit structure，提取核心论证链条 |
| ⚖️ **LogicCourt 联邦法庭** | 多智能体图引擎（PLAN→HARVEST→AUDIT→SYNTHESIZE→EVOLVE），四色置信度评估 |
| 🌐 **WitnessExpert 联网证人** | 自动检索外部证据，与本地证据交叉验证 |
| 🎯 **精准证据溯源** | 答案精确到页码和段落，附带来源颜色标识 |
| 📊 **phase_log 白盒时间线** | 每个推理阶段的耗时/状态/结果数结构化输出，渲染为飞书互动卡片 |
| 🧬 **主权演化** | 质证产生的共识自动回填知识库，形成持续进化闭环 |
| 📜 **Git 版本追溯** | 每个语义切片都有 Git 历史，支持回滚和审计 |

### 适用场景

- 📄 **合同审查**：发现条款矛盾、责任不清、风险漏洞
- 📑 **论文审计**：验证论证链条、检查引用完整性
- ⚖️ **法律文书**：比对证据链、发现逻辑断层
- 📊 **招股书/财报**：交叉验证数据一致性

---

## 🚀 快速开始

### 系统要求

- Python 3.10+
- 飞书 Bitable（作为知识库持久层）
- lark-cli（用于飞书消息发送）

### 获取 API Key

| 服务 | 用途 | 注册地址 |
|------|------|---------|
| 火山引擎 (Volcengine) | LLM doubao-2.0 | https://console.volcengine.com/ark |
| SiliconFlow | 向量模型 + VLM | https://cloud.siliconflow.cn/ |
| 飞书开放平台 | Bitable + 消息推送 | https://open.feishu.cn/ |

### 配置

复制 `.env.example` 为 `.env` 并填入：

```ini
# 火山引擎 LLM
LLM_API_KEY=your_ark_api_key
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL_NAME=doubao-2.0

# 向量模型
EMBEDDING_API_KEY=sk-xxxxxxxxx
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL_NAME=BAAI/bge-m3

# 飞书 Bitable
FEISHU_APP_ID=cli_xxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxx
FEISHU_BITABLE_TOKEN=xxxxxxxxx
```

### 使用

```bash
# 导入 PDF 文档
python -m spine_interaction.cli ingest your_document.pdf

# 单文档质证
python -m spine_interaction.cli ask "文档的核心论点是什么？" -d <doc_id>

# 跨文档质证
python -m spine_interaction.cli ask "所有文档中对 X 的描述是否一致？"

# 列出文档
python -m spine_interaction.cli list

# 启动 MCP Server（供 Aily 等 AI 代理调用）
spinedoc-mcp
```

---

## 🏛️ 架构概览

```
┌──────────────────────────────────────────────────────────────────┐
│                        交互层 (Interaction Layer)                 │
│                                                                  │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────────────┐   │
│  │   CLI    │  │  MCP Server  │  │  LarkCardBuilder          │   │
│  │ (spine)  │  │ (4 tools)    │  │  (phase_log → 飞书卡片)   │   │
│  └────┬─────┘  └──────┬───────┘  └────────────┬─────────────┘   │
│       │               │                       │                  │
│       └───────────────┼───────────────────────┘                  │
│                       │                                          │
│               ┌───────▼────────┐                                 │
│               │  SpineEngine   │                                 │
│               │  (核心引擎)      │                                 │
│               └───────┬────────┘                                 │
│                       │                                          │
└───────────────────────┼──────────────────────────────────────────┘
                        │
┌───────────────────────┼──────────────────────────────────────────┐
│                       ▼                                          │
│            逻辑层 (Logic Layer)                                   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              LogicCourt 联邦法庭图引擎                     │   │
│  │                                                          │   │
│  │   PLAN ──→ HARVEST ──→ AUDIT ──→ SYNTHESIZE ──→ EVOLVE  │   │
│  │   路由拆分   证据采集     冲突审计    判决签署     异步回填 │   │
│  │              │        │                                  │   │
│  │         ┌────┴────────┴────┐                             │   │
│  │         │  SovereignSentry │  ◁── 本地检索 + Reranker   │   │
│  │         │  WitnessExpert   │  ◁── 联网检索 + Web Search │   │
│  │         └─────────────────┘                             │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│        每个阶段产出 → phase_log[{step, status, duration_s,      │
│                        detail}] → 结构化透传至交互层             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                        │
┌───────────────────────┼──────────────────────────────────────────┐
│                       ▼                                          │
│            持久层 (Persistence Layer)                             │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                      │
│  │  飞书 Bitable     │  │  Git Version     │                      │
│  │  (documents表 +   │  │  Control         │                      │
│  │   chunks表)       │  │  (语义切片追溯)   │                      │
│  └──────────────────┘  └──────────────────┘                      │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                      │
│  │  A-MEM           │  │  Galaxy 星系路由  │                      │
│  │  (智能记忆层)     │  │  (跨文档聚类)     │                      │
│  └──────────────────┘  └──────────────────┘                      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### LogicCourt 联邦法庭工作流

SpineDoc 的核心推理引擎是一个多智能体图，每个阶段产出**结构化 phase_log**：

| 阶段 | 职责 | phase_log 明细 |
|------|------|----------------|
| **PLAN** | 查询路由拆分（多文档时） | `N 个子查询` |
| **HARVEST** | 本地 + 联网并行证据采集 | `N 条证据` |
| **AUDIT** | 逻辑冲突检测 + 状态裁剪 | `N 处冲突 \| N 条活跃` |
| **SYNTHESIZE** | 首席法官判决签署 | `N 条客观真理` |
| **EVOLVE** | 异步共识回填知识库 | 异步 dispatch |

phase_log 的结构：
```json
{"step": "HARVEST", "status": "done", "duration_s": 29.5, "detail": "7 条证据"}
```

### 单文档 vs 跨文档路径

| 场景 | 路由 | 特点 |
|------|------|------|
| **单文档** (`-d <doc_id>`) | documents表 → chunks表 直路 | 跳过 PLAN，快 2x |
| **跨文档** (`doc_id="all"`) | documents → galaxy → chunks 星系路由 | 聚类后发散检索 |

### MCP Server (Model Context Protocol)

提供 4 个标准化工具，供 Aily 等 AI 代理直接调用：

| 工具 | 功能 |
|------|------|
| `spinedoc_ingest` | 导入文档（幂等） |
| `spinedoc_ask` | 单文档质证 |
| `spinedoc_ask_all` | 跨文档质证 |
| `spinedoc_list_docs` | 列出已导入文档 |

MCP 输出包含 `verdict` + `evidence_trace` + `phase_log` 三个结构化字段，Aily 拿到后可直接渲染飞书互动卡片。

```bash
# 启动 MCP Server
spinedoc-mcp
```

### 飞书互动卡片 (phase_log 时间线)

`LarkCardBuilder` 将 phase_log 渲染为飞书卡片可视化时间线：

```
┌─────────────────────────────────────┐
│ 🔍 SpineDoc 检索分析报告            │
├─────────────────────────────────────┤
│ 🔍 查询：文档的核心架构是什么         │
├─────────────────────────────────────┤
│ 🟢 HARVEST      29s  7条证据       │
│ 🟢 AUDIT         0s  无冲突         │
│ 🟢 SYNTHESIZE   60s  9条客观真理    │
│ 🟢 EVOLVE        0s  异步回填中     │
├─────────────────────────────────────┤
│ 判决书：根据检索结果...              │
├─────────────────────────────────────┤
│ 🎯 置信度: 0.95 🟢  📚 来源: 3个   │
├─────────────────────────────────────┤
│ 📎 证据溯源：                        │
│ 🟢 [本地] 主张1... P5               │
│ 🟡 [联网] 主张2...                   │
├─────────────────────────────────────┤
│ [🔍溯源]  [🚩报告偏差]              │
└─────────────────────────────────────┘
```

### Aily 集成路径

```
用户 → 飞书 Aily
  │  Aily 识别意图 → 调用 MCP tool
  ▼
MCP Server (spinedoc_ask)
  │  LogicCourt 执行 → phase_log 记录
  ▼
JSON Response: {verdict, evidence_trace, phase_log}
  │
  ▼
Aily 渲染飞书互动卡片（含可视化时间线）
```

---

## 🔧 配置

### 环境变量

```ini
# LLM（火山引擎 doubao-2.0）
LLM_API_KEY=your_ark_api_key
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL_NAME=doubao-2.0

# 向量模型
EMBEDDING_API_KEY=sk-xxxxxxxxx
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL_NAME=BAAI/bge-m3
EMBEDDING_DIMENSION=1024

# 飞书 (Bitable + 消息推送)
FEISHU_APP_ID=cli_xxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxx
FEISHU_BITABLE_TOKEN=xxxxxxxxx
FEISHU_DEFAULT_CHAT_ID=oc_xxxxxxxxx

# 飞书 Aily 集成（可选）
FEISHU_AILY_AUTH_ID=cli_xxxxxxxxx
FEISHU_AILY_AUTH_SECRET=xxxxxxxxx
```

### 支持的其他 LLM

```ini
# OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o

# 自定义
LLM_BASE_URL=https://your-custom-api.com/v1
LLM_MODEL_NAME=your-model-name
```

---

## ❓ 常见问题

### Q: 为什么置信度都是 0.40？
A: 0.40 是单文档检索的基准置信度。更高置信度需要：
- 多文档 corroboration（0.60-0.80）
- 联网证据支持（0.80-0.95）
- 同行评审/权威来源（0.95+）

### Q: 导入文档后状态一直是 "Processing…"？
A: 可能原因：
1. Bitable 配置无效：检查 `FEISHU_BITABLE_TOKEN`
2. API Key 无效：检查火山引擎凭证
3. 飞书开放平台权限不足

### Q: 联网搜索失败？
A: 检查：
1. 飞书 config API 是否配置了 Web Search 能力
2. 网络连接是否正常
3. 查看日志中的详细错误信息

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- **火山引擎** - doubao-2.0 LLM 服务
- **SiliconFlow** - 向量模型和 VLM
- **智源研究院** - BAAI/bge 系列向量模型
- **飞书** - Bitable 知识库 + 互动卡片生态

---

## 📬 联系方式

- GitHub Issues: [提交问题或建议](https://github.com/yjh2222332024/Spine-open/issues)
- 邮箱：2857922968@qq.com

---

**🚀 SpineDoc - 让逻辑漏洞无所遁形**
