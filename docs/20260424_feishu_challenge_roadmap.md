# 🏛️ SpineDoc: 2026 飞书 AI 校园挑战赛落地全景规划

**版本**：1.0 (赋能企业专项版)  
**作者**：SpineDoc Team (Powered by Marily Nika & Uncle Bob Frameworks)  
**定位**：基于 MCP 协议的、具备语义级版本追踪能力的飞书长文档逻辑审计引擎。

---

## 💎 一、 产品定义与差异化 (Product Positioning)

### 1. 核心价值命题
在 2026 年的飞书生态中，SpineDoc 拒绝做平庸的“PDF 摘要器”，致力于成为企业的“逻辑守护者”。
- **从相似到逻辑**：不只是寻找文本，而是通过 **ISR (Implicit Structure Recognition)** 重构文档脊梁。
- **从对话到资产**：审计结论不流失，自动沉淀至 **Feishu Bitable (多维表格)**。
- **从黑盒到主权**：利用 **Chunk-level Git** 提供语义级版本回滚与 Diff。

### 2. 10x 差异化 (Unfair Advantage)
| 维度 | 普通 RAG 助手 | SpineDoc 审计 Agent |
| :--- | :--- | :--- |
| **颗粒度** | 文件级 / 段落级 | **语义切片级 (Git-based)** |
| **可信度** | 模型幻觉概率高 | **联邦法庭质证 + 四色置信度** |
| **追溯性** | 无法查看逻辑演进 | **支持逻辑版本 Diff 与 Revert** |
| **集成度** | 单纯的 Chat Bot | **Native MCP Server + Bitable 闭环** |

---

## 🏗️ 二、 架构策略：边界加固与端云分离

遵循 **Clean Architecture** 原则，确保系统在算力与交互之间取得完美平衡。

### 1. 核心分层
- **大脑 (Logic Engine)**：私有运行环境（PC/服务器）。负责 `Federated Court` 裁决与 `Git Manager` 版本控制。
- **手臂 (Execution Arm)**：`bin/lark-cli.exe` (MCP-Native)。负责监听、下载、上传与 Bitable 同步。
- **桥梁 (Bridge Layer)**：`LarkCliReporter`。解耦业务逻辑与飞书 API 细节，实现“无头模式”测试。

### 2. 算力主权模型 (The "Frugal" Model)
- **Edge-Cloud Split**：本地处理文本解析与向量指纹，云端（DeepSeek/豆包）仅处理高层逻辑冲突裁决。
- **Tiered Processing**：优先处理原生文本 PDF；仅在扫描件场景下按需触发云端 VLM (SiliconFlow/Qwen)。
- **Logic Cache**：基于文档哈希的逻辑缓存，相同文档 0 算力秒回。

---

## 🚀 三、 官方资源协同方案

### 1. 豆包 2.0 Pro (The New Brain)
- **定位**：开发助推器。
- **应用**：利用豆包 2.0 编写逻辑引擎的单元测试，优化 `Moderator` 裁决 Prompt，确保判决书的严谨性。

### 2. MCP (The Composable Asset)
- **定位**：集成杀手锏。
- **应用**：将 SpineDoc 包装为标准的 MCP 工具。飞书 Aily 可通过 MCP 协议直接调用 SpineDoc 的“质证”能力。

---

## 📅 四、 AIPDL 实现阶段 (2026 倒计时)

### 阶段 1：基础设施与桥接 (Foundation) —— 【已完成 60%】
- [x] 物理隔离科研代码，清理 `spine_engine.py`。
- [x] 编译 Lark CLI 二进制手臂。
- [x] 定义 `SpineReporter` 接口与 `NullReporter` 默认实现。
- [ ] **待办**：配置 `.env` 接入官方豆包 2.0 API 和飞书 App ID。

### 阶段 2：飞书深耕 (Integration) —— 【进行中】
- [ ] **Action**：完善 `LarkCliReporter` 的 Bitable 自动同步逻辑（映射问题、判决、风险标签）。
- [ ] **Action**：设计“飞书互动卡片”。通过红/黄/蓝/绿四色展示审计风险，提供一键跳转证据原文功能。

### 阶段 3：算力与合规 (Optimization)
- [ ] **Action**：实现 `is_scanned` 自动感知逻辑，保护云端 OCR 成本。
- [ ] **Action**：强化语义 Diff 报告。通过飞书 Markdown 消息展示逻辑节点的增删改。

### 阶段 4：评估与发布 (Evals & Launch)
- [ ] **Action**：建立“校园合规黄金集”（50 份带矛盾样本），跑出 SpineDoc 的准确率数据。
- [ ] **Action**：录制 180 秒 Demo：展示“手机飞书丢合同 -> Bitable 自动预警 -> 点击查看逻辑指纹”的全闭环。

---

## 🏛️ 五、 终极成功准则

### 💡 Marily Nika 的产品启发式
1. **先闭环，后优化**：优先打通“从 PDF 到 Bitable 记录”的一站式链路。
2. **场景大于功能**：在 PPT 中展示“校园赞助协议审计”这种具体、高频、带痛点的故事。

### 🛡️ Uncle Bob 的架构训诫
1. **代码即散文**：确保 `FeishuAdapter` 逻辑干净，不让 UI 细节渗透进逻辑内核。
2. **拒绝盲目进化**：任何自动生成的逻辑连接必须在 Bitable 中标明“AI 生成，待人工审核”。

---
**Document Status**: Persisted in `docs/`
**Next Strategic Step**: Configure `.env` and Run `BitableConnector` Pilot Test.
