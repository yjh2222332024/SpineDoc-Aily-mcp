# 📖 SpineDoc 配置指南

本文档详细介绍 SpineDoc 的所有配置选项和部署方案。

---

## 📋 目录

1. [快速配置（推荐）](#快速配置推荐)
2. [手动配置](#手动配置)
3. [环境变量详解](#环境变量详解)
4. [Docker 部署](#docker-部署)
5. [模型管理](#模型管理)
6. [故障排查](#故障排查)

---

## 快速配置（推荐）

### Windows 用户

```bash
# 1. 安装 PostgreSQL (Docker)
docker run -d --name spinedoc-postgres ^
  -e POSTGRES_PASSWORD=spinedoc123 ^
  -p 5432:5432 postgres:15

# 2. 运行配置向导
spine setup

# 3. 下载模型
spine models download --mirror

# 4. 检查配置
spine check
```

### macOS / Linux 用户

```bash
# 1. 安装 PostgreSQL (Docker)
docker run -d --name spinedoc-postgres \
  -e POSTGRES_PASSWORD=spinedoc123 \
  -p 5432:5432 postgres:15

# 2. 运行配置向导
spine setup

# 3. 下载模型
spine models download --mirror

# 4. 检查配置
spine check
```

---

## 手动配置

### 步骤 1：创建 .env 文件

复制模板文件：
```bash
cp .env.template .env
```

### 步骤 2：编辑配置文件

```ini
# ═══════════════════════════════════════════════════════════
# SpineDoc (阅脊) 配置文件
# ═══════════════════════════════════════════════════════════

# ========== 🗄️ 数据库配置（必需） ==========
DATABASE_URL=postgresql+asyncpg://spinedoc:spinedoc123@localhost:5432/spinedoc

# ========== 🤖 LLM 配置（必需） ==========
LLM_API_KEY=sk-your-deepseek-api-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL_NAME=deepseek-chat

# ========== 📐 向量模型配置（必需） ==========
EMBEDDING_API_KEY=sk-your-siliconflow-api-key
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL_NAME=BAAI/bge-m3
EMBEDDING_DIMENSION=1024

# ========== 👁️ VLM 配置（必需） ==========
VLM_API_KEY=sk-your-siliconflow-api-key
VLM_BASE_URL=https://api.siliconflow.cn/v1
VLM_MODEL_NAME=Qwen/Qwen2.5-VL-72B-Instruct

# ========== 🌐 联网搜索配置（可选） ==========
TAVILY_API_KEY=your-tavily-api-key
TAVILY_MAX_RESULTS=3
TAVILY_SEARCH_DEPTH=advanced

# ========== 💾 缓存配置（可选） ==========
CACHE_DIR=./ai_models
```

### 步骤 3：验证配置

```bash
spine check
```

---

## 环境变量详解

### 数据库配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 连接字符串 | `postgresql+asyncpg://spinedoc:spinedoc123@localhost:5432/spinedoc` |

**Docker Compose 用户：**
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: spinedoc123
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### LLM 配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `LLM_API_KEY` | LLM 服务 API Key | - |
| `LLM_BASE_URL` | LLM API 基础 URL | `https://api.deepseek.com/v1` |
| `LLM_MODEL_NAME` | LLM 模型名称 | `deepseek-chat` |

**支持的 LLM 提供商：**

| 提供商 | Base URL | 推荐模型 |
|--------|---------|---------|
| DeepSeek | `https://api.deepseek.com/v1` | `deepseek-chat` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o` |
| Moonshot | `https://api.moonshot.cn/v1` | `moonshot-v1-128k` |
| 硅基流动 | `https://api.siliconflow.cn/v1` | `deepseek-ai/DeepSeek-V3` |

### 向量模型配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `EMBEDDING_API_KEY` | SiliconFlow API Key | - |
| `EMBEDDING_BASE_URL` | 向量模型 API URL | `https://api.siliconflow.cn/v1` |
| `EMBEDDING_MODEL_NAME` | 向量模型名称 | `BAAI/bge-m3` |
| `EMBEDDING_DIMENSION` | 向量维度 | `1024` |

### VLM 配置

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `VLM_API_KEY` | VLM 服务 API Key | - |
| `VLM_BASE_URL` | VLM API 基础 URL | `https://api.siliconflow.cn/v1` |
| `VLM_MODEL_NAME` | VLM 模型名称 | `Qwen/Qwen2.5-VL-72B-Instruct` |

### 联网搜索配置（可选）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `TAVILY_API_KEY` | Tavily API Key | - |
| `TAVILY_MAX_RESULTS` | 最大搜索结果数 | `3` |
| `TAVILY_SEARCH_DEPTH` | 搜索深度 | `advanced` |

### 缓存配置（可选）

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CACHE_DIR` | 模型缓存目录 | `./ai_models` |

---

## Docker 部署

### 完整 Docker Compose 部署

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  spinedoc:
    build: .
    environment:
      - DATABASE_URL=postgresql+asyncpg://spinedoc:spinedoc123@postgres:5432/spinedoc
      - LLM_API_KEY=${LLM_API_KEY}
      - EMBEDDING_API_KEY=${EMBEDDING_API_KEY}
    volumes:
      - ./ai_models:/app/ai_models
      - ./storage:/app/storage
    depends_on:
      - postgres
    ports:
      - "8000:8000"

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=spinedoc123
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

volumes:
  postgres_data:
```

启动：
```bash
docker-compose up -d
```

---

## 模型管理

### 查看模型列表

```bash
spine models list
```

输出：
```
📋 模型列表
  ○ BAAI/bge-m3 [必需] - 智源 BGE-M3 向量模型 (多语言) - ~2.2GB
  ○ BAAI/bge-small-zh-v1.5 [必需] - 智源 BGE 小型中文向量模型 - ~200MB
  ○ stepfun-ai/GOT-OCR2_0 [可选] - GOT 通用 OCR 模型 - ~2GB
  ○ PaddleOCR v4 [必需] - PaddleOCR 中文检测 + 识别模型 - ~500MB
  ✓ KeyBERT (sentence-transformers) [可选] - 基于 BERT 的关键词提取 - ~500MB
```

### 下载模型

```bash
# 下载必需模型
spine models download

# 下载所有模型
spine models download --all

# 使用国内镜像加速
spine models download --mirror

# 组合使用
spine models download --all --mirror
```

### 清理模型缓存

```bash
# 删除所有模型缓存
spine models clean

# 或手动删除
rm -rf ~/.cache/spinedoc
rm -rf ~/.cache/huggingface/hub/models--*
```

### 自定义模型缓存位置

```bash
# 方法 1：环境变量
export SPINEDOC_CACHE_DIR=/path/to/your/cache

# 方法 2：在 .env 中配置
CACHE_DIR=/path/to/your/cache
```

---

## 故障排查

### 问题 1：数据库连接失败

**症状：**
```
Error: Could not connect to database
```

**解决方案：**
```bash
# 检查 Docker 容器
docker ps | grep postgres

# 如果容器未运行，启动它
docker start spinedoc-postgres

# 测试连接
psql postgresql://spinedoc:spinedoc123@localhost:5432/spinedoc
```

### 问题 2：API Key 无效

**症状：**
```
Error: Invalid API key
```

**解决方案：**
1. 检查 `.env` 文件中的 API Key 是否正确
2. 访问服务商官网验证 Key 是否有效
3. 运行 `spine check` 验证配置

### 问题 3：模型下载失败

**症状：**
```
Error: Failed to download model
```

**解决方案：**
```bash
# 使用镜像加速
spine models download --mirror

# 检查网络连接
ping hf-mirror.com

# 手动下载（高级用户）
huggingface-cli download BAAI/bge-m3 --cache-dir ./ai_models
```

### 问题 4：导入文档后状态一直是 "Processing…"

**症状：**
```
文档状态：Processing…
```

**解决方案：**
```bash
# 1. 检查 PostgreSQL 是否运行
docker ps | grep postgres

# 2. 检查 API Key 配置
spine check

# 3. 检查模型是否已下载
spine models list

# 4. 查看详细日志
# （查看终端输出或日志文件）
```

### 问题 5：置信度显示 0.00

**症状：**
```
颜色：YELLOW  置信度：0.00
```

**解决方案：**
这是正常现象。0.40 是单文档检索的基准置信度。

获取更高置信度：
- 多文档检索：0.60-0.80
- 启用联网搜索：`spine ask "问题" --online`
- 增加文档数量

---

## 📬 获取帮助

如果以上方法无法解决问题：

1. 查看 GitHub Issues：[提交问题](https://github.com/yjh2222332024/Spine-open/issues)
2. 发送邮件至：2857922968@qq.com
3. 查看项目文档：`docs/` 目录

---

**最后更新：** 2026-04-16
