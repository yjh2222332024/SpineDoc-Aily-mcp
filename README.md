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
| ⚖️ **联邦法庭质证** | 多智能体辩论 + 四色置信度评估，暴露逻辑漏洞 |
| 🌐 **联网证人** | 自动检索外部证据，触发知识库自我更新 |
| 📜 **Git 版本追溯** | 每个语义切片都有 Git 历史，支持回滚和审计 |
| 🎯 **精准定位** | 答案精确到页码和段落，附带逻辑溯源证据链 |

### 适用场景

- 📄 **合同审查**：发现条款矛盾、责任不清、风险漏洞
- 📑 **论文审计**：验证论证链条、检查引用完整性
- ⚖️ **法律文书**：比对证据链、发现逻辑断层
- 📊 **招股书/财报**：交叉验证数据一致性

---

## 🚀 快速开始

### 系统要求

- Python 3.10+
- Docker（用于 PostgreSQL）
- Windows 11 / macOS / Linux

### 第一步：安装 PostgreSQL

使用 Docker 一键安装：

```bash
# Windows (PowerShell)
docker run -d --name spinedoc-postgres ^
  -e POSTGRES_PASSWORD=spinedoc123 ^
  -p 5432:5432 postgres:15

# macOS / Linux
docker run -d --name spinedoc-postgres \
  -e POSTGRES_PASSWORD=spinedoc123 \
  -p 5432:5432 postgres:15
```

验证安装：
```bash
docker ps | grep postgres
```

### 第二步：获取 API Key

SpineDoc 使用以下云服务：

| 服务 | 用途 | 注册地址 |
|------|------|---------|
| DeepSeek | LLM（逻辑推理） | https://platform.deepseek.com/ |
| SiliconFlow | 向量模型 + VLM | https://cloud.siliconflow.cn/ |
| Tavily (可选) | 联网搜索 | https://tavily.com/ |

### 第三步：一键配置

```bash
# 运行交互式配置向导
spine setup
```

按提示输入：
1. 数据库连接字符串（直接回车使用默认值）
2. DeepSeek API Key
3. SiliconFlow API Key
4. Tavily API Key（可选，直接回车跳过）

### 第四步：下载 AI 模型

```bash
# 下载必需模型（约 2.7GB）
spine models download --mirror

# 或下载所有模型（约 5GB，包括可选模型）
spine models download --all --mirror
```

`--mirror` 使用国内镜像加速下载。

### 第五步：检查配置

```bash
spine check
```

输出示例：
```
📋 配置检查

必需配置：4/4
可选配置：1/1

  ✓ 数据库配置 [必需]
  ✓ LLM 配置 [必需]
  ✓ 向量模型配置 [必需]
  ✓ VLM 配置 [必需]
  ✓ 联网搜索 (可选) [可选]
```

### 第六步：开始使用

```bash
# 导入 PDF 文档
spine ingest your_document.pdf

# 提问（多文档检索）
spine ask "文档的核心论点是什么？"

# 提问（单文档）
spine ask "SM4 的密钥长度" -d 9b1d1195

# 提问（联网搜索，可能更新知识库）
spine ask "最新的密码学标准" --online

# 查看文档脊梁
spine tree <文档 ID>

# 查看语义切片
spine chunks <文档 ID>

# Git 版本管理
spine git history <ChunkID>
spine git revert <ChunkID> --to <commit_hash>
```

---

## 📚 命令行参考

### 核心命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `spine ingest <pdf>` | 导入 PDF 文档 | `spine ingest contract.pdf` |
| `spine ask "<问题>"` | 提问（多文档） | `spine ask "核心论点是什么"` |
| `spine ask "<问题>" -d <ID>` | 提问（单文档） | `spine ask "密钥长度" -d 9b1d1195` |
| `spine ask "<问题>" --online` | 提问（联网） | `spine ask "最新标准" --online` |
| `spine tree <ID>` | 查看文档脊梁 | `spine tree 9b1d1195` |
| `spine chunks <ID>` | 查看语义切片 | `spine chunks 9b1d1195` |
| `spine list` | 列出所有文档 | `spine list` |
| `spine preview <ID>` | 预览切片 | `spine preview 9b1d1195` |

### 配置命令

| 命令 | 说明 |
|------|------|
| `spine setup` | 运行配置向导 |
| `spine check` | 检查配置状态 |
| `spine models list` | 显示模型列表 |
| `spine models download` | 下载必需模型 |
| `spine models download --all` | 下载所有模型 |
| `spine models download --mirror` | 使用镜像加速 |
| `spine models clean` | 清理模型缓存 |

### Git 命令

| 命令 | 说明 |
|------|------|
| `spine git history <ChunkID>` | 查看 Git 历史 |
| `spine git show <ChunkID> --to <commit>` | 查看指定版本 |
| `spine git revert <ChunkID> --to <commit>` | 回滚到指定版本 |
| `spine git diff <ChunkID> -o <old> -n <new>` | 比较差异 |

---

## 🏛️ 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                     SpineDoc 架构                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   用户 CLI   │    │  配置管理   │    │  模型管理   │     │
│  │  (spine)    │    │  (.env)     │    │ (HuggingFace)│    │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘     │
│         │                  │                  │             │
│         └──────────────────┼──────────────────┘             │
│                            │                                │
│                   ┌────────▼────────┐                       │
│                   │  SpineEngine    │                       │
│                   │  (核心引擎)      │                       │
│                   └────────┬────────┘                       │
│                            │                                │
│         ┌──────────────────┼──────────────────┐             │
│         │                  │                  │             │
│  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐       │
│  │  向量检索    │   │  联邦法庭   │   │  Git 版本   │       │
│  │  (RAG)      │   │  (Collector)│   │  (Manager)  │       │
│  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘       │
│         │                  │                  │             │
│         │         ┌────────▼────────┐        │             │
│         │         │  Internet       │        │             │
│         │         │  Witness        │        │             │
│         │         └─────────────────┘        │             │
│         │                                    │             │
│  ┌──────▼────────────────────────────────────▼──────┐     │
│  │              PostgreSQL + pgvector                │     │
│  │              (向量数据库 + Git 存储)               │     │
│  └───────────────────────────────────────────────────┘     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

| 组件 | 说明 |
|------|------|
| **SpineEngine** | 核心引擎，协调所有子模块 |
| **RAG (Retrieval-Augmented Generation)** | 向量检索 + 语义理解 |
| **Federated Court** | 多智能体辩论系统 |
| **Internet Witness** | 联网证据检索 |
| **Git Manager** | 版本控制和审计追溯 |
| **TOC Distiller** | 目录结构提取和验证 |

---

## 🔧 高级配置

### 环境变量详解

`.env` 文件包含以下配置：

```ini
# 数据库（必需）
DATABASE_URL=postgresql+asyncpg://spinedoc:spinedoc123@localhost:5432/spinedoc

# LLM 配置（必需）
LLM_API_KEY=sk-xxxxxxxxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL_NAME=deepseek-chat

# 向量模型（必需）
EMBEDDING_API_KEY=sk-xxxxxxxxx
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL_NAME=BAAI/bge-m3
EMBEDDING_DIMENSION=1024

# VLM 配置（必需）
VLM_API_KEY=sk-xxxxxxxxx
VLM_BASE_URL=https://api.siliconflow.cn/v1
VLM_MODEL_NAME=Qwen/Qwen2.5-VL-72B-Instruct

# 联网搜索（可选）
TAVILY_API_KEY=xxxxxxxxx
TAVILY_MAX_RESULTS=3
```

### 自定义模型缓存目录

```bash
# 设置环境变量
export SPINEDOC_CACHE_DIR=/path/to/your/cache

# 或在 .env 中配置
CACHE_DIR=/path/to/your/cache
```

### 使用其他 LLM 提供商

SpineDoc 支持所有兼容 OpenAI API 格式的服务商：

```ini
# OpenAI
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4o

# Moonshot
LLM_BASE_URL=https://api.moonshot.cn/v1
LLM_MODEL_NAME=moonshot-v1-128k

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
1. PostgreSQL 未启动：`docker ps` 检查
2. API Key 无效：运行 `spine check` 验证
3. 模型未下载：运行 `spine models download`

### Q: 联网搜索失败？
A: 检查：
1. Tavily API Key 是否配置
2. 网络连接是否正常
3. 查看日志中的详细错误信息

### Q: 如何清理所有数据重新开始？
```bash
# 停止并删除数据库容器
docker stop spinedoc-postgres && docker rm spinedoc-postgres

# 删除配置文件
rm .env

# 删除模型缓存
spine models clean

# 重新运行配置
spine setup
```

---

## 📄 许可证

MIT License

---

## 🙏 致谢

- **DeepSeek** - 提供高性价比的 LLM 服务
- **SiliconFlow** - 提供向量模型和 VLM
- **智源研究院** - BAAI/bge 系列向量模型
- **PaddlePaddle** - PaddleOCR
- **HuggingFace** - 模型托管平台

---

## 📬 联系方式

- GitHub Issues: [提交问题或建议](https://github.com/yjh2222332024/Spine-open/issues)
- 邮箱：2857922968@qq.com

---

**🚀 SpineDoc - 让逻辑漏洞无所遁形**
