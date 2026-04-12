# 🚀 SpineDoc 启动与操作指南 (V1.0.0)

本指南旨在帮助用户快速部署并运行 SpineDoc 联邦智能 RAG 引擎。

## 1. 环境准备

### 硬件推荐
- **GPU**: NVIDIA RTX 3060 以上（推荐 RTX 4060），显存 ≥ 8GB（用于本地 OCR 高效收割）。
- **存储**: 固态硬盘，预留 ≥ 20GB 空间。

### 软件依赖
- Python 3.12+
- PostgreSQL 16+ (需安装 **pgvector** 扩展)
- 环境变量配置 (见 `.env.template`)

## 2. 快速部署

```bash
# 1. 克隆仓库
git clone https://github.com/yjh2222332024/Spine-open.git
cd Spine-open

# 2. 安装项目（这会自动注册 'spine' 命令）
pip install -e .

# 3. 配置环境变量 (关键步骤)
# 复制模板文件
cp .env.template .env
# 编辑 .env 文件，填入你的：
# - OPENAI_API_KEY 或 SILICONFLOW_API_KEY
# - DATABASE_URL (例如 postgresql+asyncpg://user:pass@localhost:5432/spine)
```

## 3. 初始化数据库

第一次运行前，需要清理并初始化数据库结构：

```bash
# 这一步会创建必要的表并安装 pgvector 插件
python scripts/force_reset_doc.py
```

## 3. 命令行操作 (CLI)

SpineDoc 提供了一键式命令行入口：

### 审计文档 (Ingest)
```bash
# 自动提取结构、OCR 并完成语义反哺
spine ingest ./my_documents/ --limit 100
```

### 发起联邦辩论 (Ask)
```bash
# 启动逻辑刺客模式，获取带物理溯源的判决书
spine ask "对比不同文档对 DES 算法安全性的评价。" --doc all
```

## 4. API 服务启动

系统集成了一个标准的 FastAPI 服务，支持 Web 接入：

```bash
# 启动后端服务
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

访问 `http://localhost:8000/docs` 查看 Swagger 文档。
