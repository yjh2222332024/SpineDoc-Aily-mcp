# SpineDoc (阅脊) - 项目上下文文档

> **版本**: V1.3.0 | **架构**: Trident v1.2.0 | **语言**: Python 3.9+

---

## 📋 项目概述

**SpineDoc** 是一款专为**超长、复杂文档**设计的高精度逻辑审计引擎。它拒绝盲目的文本切块，通过独创的 **隐式脊梁重建 (ISR)** 与 **联邦辩论 (Federated Debate)** 技术，实现物理页码级的事实溯源与逻辑纠偏。

### 核心理念
> "不要只是与 PDF 聊天，去重构它们的逻辑。"

### 核心技术
| 技术 | 说明 |
|------|------|
| **ISR (Implicit Spine Reconstruction)** | 自动探测并重建文档逻辑骨架，使检索具备"章节感知"能力 |
| **联邦辩论法庭 (V41.7)** | 多智能体蒙眼辩论与逻辑对线，冲突嗅探准确率 95% |
| **级联式语义路由** | 比 GraphRAG 节省 99% Token，精度相当 |
| **物理锚定溯源** | 100% 锚定 PDF 物理页码，实现像素级证据回溯 |

---

## 🏗️ 系统架构 (Trident 三叉戟)

```
┌─────────────────────────────────────────────────────────────────┐
│                        SpineDoc 生态                             │
├─────────────────────────────────────────────────────────────────┤
│  1. 核心 CLI (引擎层)                                            │
│     ├── spine ingest: 文档晶体化                                │
│     ├── spine ask: 联邦法庭判决                                 │
│     └── spine mcp: MCP 服务器                                   │
├─────────────────────────────────────────────────────────────────┤
│  2. MCP 协议层 (集成层)                                          │
│     ├── Claude Desktop 集成                                    │
│     ├── Cursor IDE 集成                                         │
│     └── 本地文档解析能力远程调度                                │
├─────────────────────────────────────────────────────────────────┤
│  3. 智能取证 (能力层)                                            │
│     ├── 联邦法庭 (Federated Court)                              │
│     ├── 深度导航员 (Navigator)                                  │
│     └── 量化证人 (QuantMarket)                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 目录结构
```
Spine-close/
├── spine_cli/                 # CLI 核心引擎
│   ├── main.py               # Typer CLI 入口
│   ├── core/
│   │   ├── engine.py         # SpineEngine 主引擎
│   │   ├── router.py         # 语义路由器
│   │   ├── reranker.py       # 重排序器
│   │   └── agents/           # 多智能体系统
│   │       ├── graph.py      # LangGraph 状态图
│   │       ├── federation/   # 联邦法庭节点
│   │       └── navigator/    # 深度导航插件
│   ├── indexer/              # 索引器
│   ├── llm/                  # LLM 客户端
│   └── mcp/                  # MCP 协议
├── backend/                   # FastAPI 后端
│   ├── app/
│   │   ├── api/              # REST API 端点
│   │   ├── services/         # 业务服务
│   │   │   ├── parser.py     # 混合 PDF 解析器
│   │   │   ├── rag/          # RAG 引擎
│   │   │   ├── toc/          # TOC 提取与对齐
│   │   │   └── ocr/          # OCR 服务 (SGLang + GLM)
│   │   ├── core/             # 核心配置与 DB
│   │   └── schemas/          # Pydantic 模型
│   └── migrations/           # 数据库迁移
├── docker/                    # Docker 部署
│   ├── docker-compose.yml    # 主服务编排
│   ├── docker-compose-slm.yml # SLM 服务
│   └── Dockerfile
├── evaluation/                # 评估框架
│   ├── metrics.py            # TOC/检索指标
│   ├── stress_test.py        # 压力测试
│   └── runner.py             # 完整评估运行器
├── scripts/                   # 工具脚本 (38 个)
├── tests/                     # 测试用例
├── docs/                      # 架构文档
└── examples/                  # 示例文档
```

---

## 🚀 构建与运行

### 环境要求
- **Python**: 3.9+
- **数据库**: PostgreSQL 16 + pgvector
- **缓存**: Redis 7
- **GPU (可选)**: NVIDIA GPU (用于 SGLang OCR)

### 1. 安装依赖
```bash
cd Spine-close
pip install -e .
```

### 2. 配置环境变量
```bash
# 复制模板
cp .env.template .env

# 编辑 .env，配置以下关键变量:
# - LLM_API_KEY (DeepSeek/OpenAI)
# - EMBEDDING_API_KEY (SiliconFlow)
# - DATABASE_URL (PostgreSQL)
# - REDIS_URL (Redis)
# - OCR 相关配置 (SGLang/GLM)
```

### 3. 启动基础设施 (Docker)
```bash
# 启动 PostgreSQL + Redis + SGLang OCR 服务
docker-compose up -d
```

### 4. 验证安装
```bash
# 列出知识库文档
spine list

# 摄入文档
spine ingest ./docs/my_papers/

# 发起查询
spine ask "详细对比不同文档中关于 SM4 算法分组长度的描述"
```

---

## 🛠️ CLI 命令参考

| 命令 | 说明 | 示例 |
|------|------|------|
| `spine ingest <path>` | 摄入 PDF 文档/文件夹 | `spine ingest ./papers/ --workers 6` |
| `spine ask "<query>"` | 联邦法庭判决 | `spine ask "HippoRAG 2 的核心改进" --kg` |
| `spine mcp` | 启动 MCP 服务器 | `spine mcp` |
| `spine list` | 列出已入库文档 | `spine list` |
| `spine chunks <doc_id>` | 查看语义切片 | `spine chunks abc123 --limit 20` |
| `spine compare "<topic>"` | 跨文档对比 | `spine compare "RAG vs GraphRAG"` |
| `spine tree <doc_id>` | 显示逻辑脊梁树 | `spine tree abc123` |

### Ingest 高级选项
```bash
spine ingest ./doc.pdf \
  --force \                    # 强制重新入库
  --limit 100 \                # 限制处理页数
  --toc-range "9,15" \         # 手动指定目录范围
  --ocr \                      # 强制 OCR 模式
  --font-feature \             # 使用字体特征提取
  --key "sk-xxx" \             # 注入私有 API Key
  --stop-words "./dict.txt"    # 自定义停用词
```

---

## 🧪 测试与评估

### 运行评估
```bash
# 完整评估 (TOC 准确率 + 检索 MRR + 压力测试)
python evaluation/runner.py

# 单独压力测试
python evaluation/stress_test.py

# 构建测试集
python evaluation/dataset_builder.py

# 创建 QA 标注模板
python evaluation/qa_dataset_builder.py
```

### 性能指标 (目标值)
| 指标 | 目标值 | 说明 |
|------|--------|------|
| TOC Precision | > 90% | 目录提取准确率 |
| MRR | > 0.75 | 检索排名质量 |
| Recall@5 | > 80% | 前 5 结果召回率 |
| Ingest (5000 页) | < 10 分钟 | 文档处理延迟 |
| Query (P50) | < 2 秒 | 查询响应延迟 |
| 内存峰值 (5000 页) | < 4GB | 避免 OOM |

---

## 🤖 智能体架构

### 联邦法庭 (Federated Court) - V41.7
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Distributor │ ──► │   Witness    │ ──► │  Moderator   │
│  (分发员)     │     │  (证人)      │     │  (法官)      │
└──────────────┘     └──────────────┘     └──────────────┘
                            │
                     ┌──────▼──────┐
                     │ QuantMarket │
                     │ (量化证人)  │
                     └─────────────┘
                            │
                     ┌──────▼──────┐
                     │ Integrator  │
                     │ (大法官)    │
                     └─────────────┘
```

### 节点职责
| 节点 | 职责 | 关键特性 |
|------|------|----------|
| **Distributor** | 并行调遣 PDF 证人与市场证人 | 动态分流 |
| **Witness** | 深度挖掘 PDF 物理页码 | 禁止推理，只吐论点 |
| **QuantMarket** | 实时抓取 Finnhub/DailyFX | 个股提取 |
| **Moderator** | 捕捉逻辑冲突 | 置信度红绿灯 |
| **Integrator** | 合成 JSON 判决书 | BUY/SELL 指令 |

### 深度导航员 (Navigator) - V37.0
- **Cartographer (制图师)**: 通过逻辑脊梁外推物理页码
- **Investigator (取证员)**: 在长文档深水区执行物理翻页
- **状态**: 作为 `Federated Witness` 的核心战术插件

---

## 🔧 核心模块详解

### 1. SpineEngine (`spine_cli/core/engine.py`)
```python
class SpineEngine:
    """三叉戟解耦流水线引擎"""
    
    async def ingest_document(...) -> Dict:
        # 1. 查重
        # 2. 提取 TOC (HybridParser)
        # 3. OCR 收割 (BodyAlchemist)
        # 4. 持久化骨架
        # 5. 语义反哺
        
    async def hybrid_ask(...) -> List[Dict]:
        # 启动联邦法庭
        # 返回判决书 + 证据链
```

### 2. 混合解析器 (`backend/app/services/parser.py`)
```python
class HybridParser:
    """
    支持三种模式:
    1. Metadata 提取 (原生 PDF 目录)
    2. 文本层嗅探 (目录页正则匹配)
    3. Body-Scan 锚点扫描 (无目录文档)
    """
```

### 3. RAG 引擎 (`backend/app/services/rag/engine.py`)
```python
class RAGEngine:
    """
    三级级联检索:
    1. TOC 路由：基于目录标题相似度锁定章节
    2. 向量召回：在精准范围内匹配向量
    3. Reranker: 重排序提升精度
    """
```

---

## 📦 数据模型

### Document (文档)
```python
class Document(SQLModel):
    id: UUID
    filename: str
    file_path: str
    status: ProcessingStatus
    total_pages: int
    is_scanned: bool          # 是否扫描件
    page_offset: int          # 页码偏移量
    created_at: datetime
```

### TocItem (目录项)
```python
class TocItem(SQLModel):
    id: UUID
    document_id: UUID
    title: str
    page: int                 # 逻辑页码
    level: int                # 层级 (1/2/3)
    physical_page: int        # 物理页码
    breadcrumb: str           # 完整路径
```

### Chunk (语义切片)
```python
class Chunk(SQLModel):
    id: UUID
    document_id: UUID
    toc_item_id: Optional[UUID]
    content: str
    page_number: int
    keywords: List[str]       # jieba 分词
    embedding: Vector         # pgvector
```

---

## 🔐 配置说明

### 关键环境变量
```bash
# LLM 配置
LLM_API_KEY=sk-your-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL_NAME=deepseek-chat

# 向量模型 (推荐 SiliconFlow)
EMBEDDING_API_KEY=sk-your-key
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL_NAME=BAAI/bge-m3

# 数据库
DATABASE_URL=postgresql+asyncpg://spinedoc:spinedoc123@localhost:5432/spinedoc

# Redis
REDIS_URL=redis://localhost:6379/0

# OCR 配置
OCR_STRATEGY=adaptive         # adaptive/local_only/cloud_first/fallback
OCR_BACKEND=sglang            # sglang/transformers/cloud
SGLANG_BASE_URL=http://127.0.0.1:30000/v1
OCR_USE_GPU=True
```

---

## 📊 性能对比

| 维度 | 传统 RAG | SpineDoc V1.3.0 | 提升 |
|------|----------|-----------------|------|
| 引用精度 | < 60% | **100%** (物理锚定) | 🎯 真实溯源 |
| 构建速度 | 线性增长 | **43.1s / 100 页** (并发) | 🚀 极速收割 |
| 冲突识别 | 无 | **95%** (冲突嗅探) | ⚖️ 逻辑严密 |
| Token 成本 | 高 | **节省 99%** (级联路由) | 💰 低成本 |

---

## 🧭 开发惯例

### 代码风格
- **类型注解**: 所有函数签名必须包含类型注解
- **文档字符串**: 公共类/方法必须有清晰的 docstring
- **日志记录**: 使用 `logger` 而非 `print`
- **异步优先**: I/O 操作优先使用 `async/await`

### 测试实践
```bash
# 运行单元测试
pytest tests/

# 运行 E2E 测试
python tests/run_v40_e2e.py

# 原子测试 (联邦法庭)
python tests/test_v40_atomic.py
```

### 提交规范
```
<type>(<scope>): <subject>
  |       |        |
  |       |        └─ 简短描述 (不超过 50 字)
  |       └────────── 模块名 (engine/agents/ocr/...)
  └────────────────── 类型 (feat/fix/docs/refactor/test)
```

---

## 🔍 调试工具

### 脚本库 (scripts/)
| 脚本 | 用途 |
|------|------|
| `inspect_db_chunks.py` | 检查数据库 Chunk |
| `diagnose_data_quality.py` | 数据质量诊断 |
| `test_100p_sota.py` | 百页文档 SOTA 测试 |
| `verify_full_chain_4060.py` | 全链路验证 |
| `nuke_database.py` | 清空数据库 |

### 日志级别
```python
import logging
logging.basicConfig(level=logging.INFO)  # DEBUG/INFO/WARNING/ERROR
```

---

## 📚 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](README.md) | 项目总览与快速上手 |
| [README-CLI.md](README-CLI.md) | CLI 详细用法 |
| [AGENTS.md](AGENTS.md) | 智能体舰队架构 |
| [BENCHMARK.md](BENCHMARK.md) | 性能基准测试 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构详解 |
| [evaluation/README.md](evaluation/README.md) | 评估框架指南 |

---

## 🏁 2026 路线图

### Phase 1: 引擎融合与逻辑网关 (进行中)
- [ ] 实现 `SpineGateway` 动态分流逻辑
- [ ] 将 Navigator 集成到 Federated Witness 的"二跳检索"
- [ ] 完善 QuantMarket 的个股提取鲁棒性

### Phase 2: 知识代谢与 CRUD 反哺 (待启动)
- [ ] 开发 `KnowledgePatcher`，基于法庭判决自动修补/删除过时 PDF
- [ ] 建立 `DailyAudit` 定时任务，清晨自动抓取市场动态

### Phase 3: Web 化的四色仪表盘 (待启动)
- [ ] 改造 FastAPI，实现流式事件输出
- [ ] 对接 React 前端，实现置信度溯源高亮 UI

### Phase 4: 量化实盘执行与风控 (终极目标)
- [ ] 增加 `RiskController` 节点，对 Integrator 决策执行"一票否决"
- [ ] 接入模拟盘交易接口

---

## 🤝 联系方式

- **邮箱**: 2857922968@qq.com
- **GitHub**: [yjh2222332024](https://github.com/yjh2222332024/Spine-open)

---

*Powered by SpineDoc Trident Engine v1.3.0 | MIT License*
