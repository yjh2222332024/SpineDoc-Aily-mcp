# 📚 SpineDoc 文档索引

本文档汇总了 SpineDoc 的所有官方文档和资源。

---

## 🚀 快速开始

| 文档 | 说明 | 适合人群 |
|------|------|---------|
| [README.md](../README.md) | 项目概述和快速上手 | 所有用户 |
| [CONFIGURATION.md](CONFIGURATION.md) | 详细配置指南 | 新用户、运维人员 |
| [CLI_USAGE.md](CLI_USAGE.md) | 命令行使用指南 | 所有用户 |

---

## 📖 核心文档

### 用户指南

| 文档 | 说明 |
|------|------|
| [CONFIGURATION.md](CONFIGURATION.md) | 环境配置、Docker 部署、模型管理 |
| [CLI_USAGE.md](CLI_USAGE.md) | 所有 CLI 命令的详细用法 |

### 技术文档

| 文档 | 说明 |
|------|------|
| [20260414_galaxy_breathing_design.md](20260414_galaxy_breathing_design.md) | Galaxy Breathing 架构设计 |
| [20260414_work_log_and_pm_plan.md](20260414_work_log_and_pm_plan.md) | 开发日志和项目计划 |

---

## 📋 按使用场景分类

### 我是新用户，想快速体验

1. 阅读 [README.md](../README.md) 了解项目
2. 按照 [CONFIGURATION.md](CONFIGURATION.md) 的"快速配置"章节进行安装
3. 参考 [CLI_USAGE.md](CLI_USAGE.md) 学习基本命令

### 我是运维人员，需要部署生产环境

1. 阅读 [CONFIGURATION.md](CONFIGURATION.md) 的"Docker 部署"章节
2. 参考"环境变量详解"配置生产环境
3. 查看"故障排查"解决常见问题

### 我是开发者，想了解架构

1. 阅读 [README.md](../README.md) 的"架构概览"
2. 查看技术文档了解设计细节
3. 阅读源代码注释

---

## 🔧 配置文件参考

| 文件 | 说明 |
|------|------|
| [.env.template](../.env.template) | 配置文件模板 |
| [spine_setup.py](../spine_setup.py) | 交互式配置脚本 |
| [setup.bat](../setup.bat) | Windows 一键配置脚本 |

---

## 📦 脚本工具

| 脚本 | 说明 |
|------|------|
| [scripts/download_models.py](../scripts/download_models.py) | AI 模型下载器 |
| [spine_setup.py](../spine_setup.py) | 配置向导 |

---

## 🌐 外部资源

### API 服务

| 服务 | 用途 | 网址 |
|------|------|------|
| DeepSeek | LLM | https://platform.deepseek.com/ |
| SiliconFlow | 向量模型 + VLM | https://cloud.siliconflow.cn/ |
| Tavily | 联网搜索 | https://tavily.com/ |

### 模型仓库

| 模型 | 仓库 |
|------|------|
| BAAI/bge-m3 | https://huggingface.co/BAAI/bge-m3 |
| BAAI/bge-small-zh-v1.5 | https://huggingface.co/BAAI/bge-small-zh-v1.5 |
| GOT-OCR2_0 | https://huggingface.co/stepfun-ai/GOT-OCR2_0 |

### 相关项目

| 项目 | 说明 |
|------|------|
| PostgreSQL | https://www.postgresql.org/ |
| pgvector | https://github.com/pgvector/pgvector |
| PaddleOCR | https://github.com/PaddlePaddle/PaddleOCR |

---

## 📬 获取帮助

### 文档未解答的问题

1. **GitHub Issues**: [提交问题](https://github.com/yjh2222332024/Spine-open/issues)
2. **邮箱**: 2857922968@qq.com

### 贡献文档

欢迎提交 PR 改进文档！

---

## 📝 文档更新日志

| 日期 | 更新内容 |
|------|---------|
| 2026-04-16 | 创建文档索引、配置指南、CLI 使用指南 |
| 2026-04-16 | 更新 README.md 为用户友好版本 |

---

**最后更新：** 2026-04-16
