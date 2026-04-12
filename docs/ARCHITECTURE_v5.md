# SpineDoc v5.0 纯图 PDF 支持 - 架构设计文档

**版本**: v5.0  
**日期**: 2026 年 3 月 27 日  
**状态**: ✅ 核心功能完成

---

## 📋 目录

1. [项目概述](#项目概述)
2. [核心架构](#核心架构)
3. [数据模型](#数据模型)
4. [风险与缓解](#风险与缓解)
5. [API 设计](#api 设计)
6. [测试策略](#测试策略)

---

## 项目概述

### 核心目标

解决 LLM 处理长文档（500 页+）时"切得碎、丢逻辑"的问题，特别支持**纯图 PDF（扫描件）**的端到端处理。

### 技术亮点

| 特性 | 传统 RAG | SpineDoc v5.0 |
|------|---------|---------------|
| **文档理解** | 固定长度切片 | TOC 驱动的语义切片 |
| **纯图支持** | ❌ 不支持 | ✅ OCR + VLM 双重保障 |
| **溯源精度** | 片段级 | 物理页码级 |
| **检索逻辑** | 向量相似度 | 级联检索 + 质量加权 |

---

## 核心架构

### 1. 四层解析架构

```
backend/app/services/ocr/
├── models.py                 # SpineObject 数据模型
├── integration/
│   └── architect_parser.py   # ArchitectVisualParser (主引擎)
├── worker.py                 # OCRWorker (封装 RapidOCR/PaddleOCR)
└── __init__.py
```

### 2. 三种工作模式

```python
# 模式 1: 纯本地 OCR (最快，免费)
parser = ArchitectVisualParser(mode="local_only")

# 模式 2: LLM 清洗 (平衡)
parser = ArchitectVisualParser(mode="llm_refine")

# 模式 3: VLM 验证 (最高精度，智能触发)
parser = ArchitectVisualParser(mode="auto", vlm_threshold=0.7)
```

### 3. 智能路由策略

```
PDF 输入
    ↓
┌─────────────────────────────┐
│ 1. Metadata 检测 (<100ms)    │
│    doc.get_toc() → 有 → 返回  │
└─────────────────────────────┘
    ↓ 无
┌─────────────────────────────┐
│ 2. 文本层检测 (<500ms)       │
│    每页>100 字符 → 正则提取    │
└─────────────────────────────┘
    ↓ 纯图
┌─────────────────────────────┐
│ 3. OCR 视觉识别 (30-60 秒)    │
│    ArchitectVisualParser     │
│    ↓ 置信度 < 0.7?           │
│    ↓ 是 → 触发 VLM 验证       │
└─────────────────────────────┘
    ↓
┌─────────────────────────────┐
│ 4. LLM 二次优化 (可选)        │
│    clean_toc(ocr_text)      │
└─────────────────────────────┘
```

---

## 数据模型

### SpineObject 2.0

```python
@dataclass
class SpineObject:
    # 基础字段
    title: str
    page: int                    # 逻辑页码
    level: int                   # 层级
    content: str
    
    # 纯图 PDF 增强字段
    physical_page: int           # 物理页码（关键！）
    ocr_confidence: float        # OCR 置信度 (0.0-1.0)
    is_scanned: bool             # 是否扫描件
    ocr_engine: str              # OCR 引擎
    
    # 特殊内容标记
    has_table: bool
    has_formula: bool
    has_image: bool
    
    # 位置信息
    bbox: List[List[int]]        # 目录项坐标
    
    # 元数据
    breadcrumb: str              # 层级路径
    source: str                  # 来源 (ocr/llm_refined)
```

### 数据库扩展

```python
class Chunk(SQLModel, table=True):
    # ... 原有字段 ...
    
    # 🆕 纯图 PDF 支持：元数据 JSON 字段
    metadata_json: Optional[Dict[str, Any]] = Field(
        default_factory=dict, 
        sa_column=Column(JSON)
    )
    # 包含：physical_page, ocr_confidence, is_scanned 等
```

---

## 风险与缓解

### 1. OCR Worker 并发安全 ⚠️

**风险**: PaddleOCR/RapidOCR 的 C++ 动态库在高并发下可能崩溃

**缓解措施**:
```python
# ✅ 已实施：使用 ProcessPoolExecutor
from concurrent.futures import ProcessPoolExecutor

_process_pool = None

def _get_process_pool():
    global _process_pool
    if _process_pool is None:
        _process_pool = ProcessPoolExecutor(max_workers=4)
    return _process_pool

# 在 ArchitectVisualParser 中
def _get_executor(self):
    if self._executor is None:
        if self.use_process_pool:
            self._executor = _get_process_pool()  # 进程池
        else:
            self._executor = ThreadPoolExecutor()  # 线程池（快速但不安全）
    return self._executor
```

**生产建议**:
- 使用 `ProcessPoolExecutor` (默认)
- 或使用独立的 Celery 任务队列
- 监控 `dmesg` 日志检测 segfault

---

### 2. VLM 成本与延迟 ⚠️

**风险**: 云端 VLM API 延迟 1-3 秒，成本较高

**缓解措施**:
```python
# ✅ 已实施：智能触发策略
parser = ArchitectVisualParser(
    mode="auto",              # 智能模式
    vlm_threshold=0.7         # 仅当 OCR 置信度 < 0.7 时触发
)

# 内部逻辑
if avg_ocr_confidence < self.vlm_threshold:
    vlm_result = await self._vlm_verify_toc_page(img_base64)
```

**成本对比**:

| 策略 | 延迟 | 成本/1000 页 | 适用场景 |
|------|------|-------------|---------|
| local_only | 30 秒 | ¥0 | 大多数文档 |
| auto (智能) | 30-33 秒 | ¥0.5-2 | 混合文档 |
| vlm_verify | 35-40 秒 | ¥5-10 | 高精度需求 |

**UI 建议**:
```
[ ] 启用高精度模式 (额外 +¥0.01/页，延迟 +3 秒)
```

---

### 3. Fuzzy TOC Matching ⚠️

**风险**: OCR 产生的错别字导致匹配失败

**示例**:
- "第 1 章" vs "第一章"
- "引言" vs "引官" (OCR 错误)

**当前方案**: 硬匹配 (生产环境可能不够)

**推荐改进**:
```python
# TODO: 引入 fuzzywuzzy 或 rapidfuzz
from rapidfuzz import fuzz

def _match_toc_title(ocr_title: str, llm_title: str) -> bool:
    """模糊匹配 TOC 标题"""
    score = fuzz.ratio(ocr_title, llm_title)
    return score > 85  # 85% 相似度阈值

# 在 _merge_toc_results 中使用
for llm_item in llm_toc:
    matched = None
    for ocr_item in ocr_toc:
        if _match_toc_title(ocr_item["title"], llm_item["title"]):
            matched = ocr_item
            break
```

**安装**:
```bash
pip install rapidfuzz  # 比 fuzzywuzzy 快 10 倍
```

---

## API 设计

### 1. 文档上传与解析

```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data

{
  "file": <pdf_file>,
  "ocr_mode": "auto",           // local_only | llm_refine | vlm_verify | auto
  "vlm_threshold": 0.7,         // VLM 触发阈值
  "use_gpu": true
}
```

**响应**:
```json
{
  "document_id": "uuid",
  "status": "processing",
  "estimated_time": 45,
  "toc_preview": [
    {"title": "第一章 引言", "page": 1, "level": 1},
    {"title": "1.1 研究背景", "page": 2, "level": 2}
  ]
}
```

### 2. 级联检索

```http
POST /api/v1/rag/query
Content-Type: application/json

{
  "query": "什么是 ISR 技术？",
  "document_id": "uuid",
  "limit": 5,
  "enable_ocr_weighting": true,  // OCR 置信度加权
  "rerank": true
}
```

**检索流程**:
```
1. 脊梁路由 → 匹配相关章节
2. 向量检索 → Top 2N 候选
3. OCR 加权 → distance *= (0.5 + ocr_confidence)
4. Rerank → 云端 API 精排
5. 返回 → Top 5 + 溯源信息
```

**响应**:
```json
{
  "answer": "ISR 是隐式脊梁重建技术...",
  "sources": [
    {
      "content": "...",
      "breadcrumb": "第三章 > 3.1 ISR 原理",
      "page": 45,
      "physical_page": 48,      // 纯图 PDF 关键！
      "ocr_confidence": 0.92,
      "is_scanned": true
    }
  ],
  "metadata": {
    "query_time_ms": 2350,
    "total_chunks": 5,
    "rerank_used": true
  }
}
```

---

## 测试策略

### 1. 单元测试

```bash
# OCR 模块
pytest backend/app/services/ocr/ -v

# 级联检索
pytest backend/app/services/rag/ -v
```

### 2. 集成测试

```bash
# 纯图 PDF 完整流程
python test_local_only.py       # 本地 OCR 模式
python test_vlm_only.py         # VLM 验证模式
python test_cascading_retrieval.py  # 级联检索
```

### 3. 性能基准

| 测试项 | 目标 | 当前 | 状态 |
|--------|------|------|------|
| 目录提取准确率 | >85% | 82% | ⚠️ 待优化 |
| VLM 验证成功率 | >95% | 95% | ✅ |
| 检索延迟 | <5 秒 | 2.3 秒 | ✅ |
| OCR 置信度加权 | 生效 | 生效 | ✅ |

---

## 部署指南

### Docker Compose (生产环境)

```yaml
version: '3.8'

services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_USER: spinedoc
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: spinedoc
  
  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://spinedoc:${DB_PASSWORD}@db:5432/spinedoc
      LLM_API_KEY: ${LLM_API_KEY}
      VLM_API_KEY: ${VLM_API_KEY}
      OCR_USE_GPU: "true"
      NVIDIA_VISIBLE_DEVICES: all
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
  
  worker:  # 独立的 OCR 工作进程
    build: ./backend
    command: celery -A app.worker worker --concurrency=4
    environment:
      OCR_USE_PROCESS_POOL: "false"  # Celery 已提供进程隔离
```

### 环境变量

```bash
# .env
DATABASE_URL=postgresql+asyncpg://spinedoc:password@localhost:5432/spinedoc

# LLM 配置
LLM_API_KEY=sk-xxxxx
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL_NAME=deepseek-chat

# VLM 配置 (可选)
VLM_API_KEY=sk-xxxxx
VLM_BASE_URL=https://api.siliconflow.cn/v1
VLM_MODEL_NAME=Qwen/Qwen3-VL-8B-Instruct

# OCR 配置
OCR_USE_GPU=true
OCR_STRATEGY=auto  # local_only | cloud_first | fallback | adaptive

# 向量模型
EMBEDDING_API_KEY=sk-xxxxx
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL_NAME=BAAI/bge-m3
```

---

## 性能优化建议

### 1. OCR 加速

```python
# 使用 GPU OCR
settings.OCR_USE_GPU = True

# 批量处理（多页并行）
asyncio.gather(*[ocr_page(img) for img in images])

# 缓存 OCR 结果
@cache(ttl="24h")
async def cached_ocr_page(img_hash: str):
    ...
```

### 2. 向量检索优化

```python
# 使用 pgvector 的索引
CREATE INDEX ON chunk USING ivfflat (embedding vector_cosine_ops);

# 限制检索范围
WHERE document_id = 'uuid'  # 先过滤文档
```

### 3. 缓存策略

```python
# Redis 缓存检索结果
@redis_cache(ttl="1h", key_prefix="rag")
async def cached_search(query: str, doc_id: str):
    ...
```

---

## 待办事项

- [ ] 集成 `rapidfuzz` 实现模糊匹配
- [ ] 添加 Celery 任务队列支持
- [ ] 实现 OCR 结果缓存
- [ ] 完善监控和日志
- [ ] 编写用户文档
- [ ] 性能基准测试自动化

---

## 相关文档

- [README.md](../README.md) - 项目介绍
- [SETUP.md](../SETUP.md) - 开发环境配置
- [AGENTS.md](../AGENTS.md) - 团队协作指南
- [BENCHMARK.md](../BENCHMARK.md) - 性能基准

---

**最后更新**: 2026 年 3 月 27 日  
**维护者**: SpineDoc Team
