# 📜 联网证人系统实现日志 (2026-04-15)

## 1. 实现概览

**时间**: 2026-04-15  
**状态**: ✅ 核心功能完成，测试通过  
**测试查询**: "信息安全中的加密方法有哪些？"

---

## 2. 架构决策

### 2.1 为什么选 Tavily？

| 方案 | 价格 | 优势 | 劣势 |
|------|------|------|------|
| **Tavily** | ~$8/1k 搜索 | 专为 LLM 设计，内置意图分类、置信度评分 | 成本较高 |
| **SERPER + Jina** | ~$1/1k 搜索 | 便宜，可控 | 需要自己处理数据清洗 |
| **纯本地** | $0 | 零成本 | 无时效性 |

**决策**：选择 Tavily，因为：
1. **RAG-ready**：返回的数据已经过清洗，适合直接入证据库
2. **置信度内置**：Tavily 返回 `score` 字段，可作为基础权威分
3. **开发成本低**：官方 SDK 处理了重试、序列化等复杂逻辑

---

### 2.2 证人入场时机

**决策**：联网证人与本地证人**并行入场**

```
阶段 1: Distributor 传唤本地证人
         ↓
阶段 2: Collector 并行执行
         ├── 本地取证（每个文档）
         └── 联网取证（Tavily API）
         ↓
阶段 3: Moderator 统一裁决所有证据
```

**理由**：
1. **异步并行**：本地和联网检索互不阻塞
2. **证据统一**：互联网证据和本地证据格式一致，Moderator 无需区分
3. **成本可控**：只在必要时调用 Tavily（可加开关）

---

## 3. 核心组件

### 3.1 InternetWitness

**文件**: `backend/app/services/intelligence/court/internet_witness.py`

```python
class InternetWitness:
    """
    ⚖️ 联网证人：法庭的外部信息补充官。
    设计原则：故障隔离、异步友好、成本可控
    """
    
    async def summon(queries: List[str], query_type: str) -> Dict:
        """
        传唤联网证人，返回证据包
        
        返回结构：
        {
            "doc_id": "INTERNET_xxx",
            "galaxy_id": "INTERNET",
            "galaxy_name": "互联网证人",
            "evidence_chunks": [
                {
                    "id": "internet_xxx",
                    "content": "摘要内容",
                    "source_url": "https://...",
                    "source_title": "标题",
                    "published_date": "2025-01-01",
                    "confidence": 0.42,  # 动态计算
                    "is_internet": True
                }
            ],
            "scout_queries": [...],
            "is_internet": True
        }
        ```
    """

### 3.2 动态置信度算法

**公式**: `W_final = W_base × W_authority × W_recency`

```python
# W_base: Tavily 返回的基础分数（0-1）
w_base = result.get('score', 0.8)

# W_authority: 域名权威分
DOMAIN_AUTHORITY = {
    'gov.cn': 1.0, 'ac.cn': 1.0, 'edu.cn': 1.0,
    'arxiv.org': 0.95, 'wikipedia.org': 0.9,
    'github.com': 0.85, 'zhihu.com': 0.7,
    'csdn.net': 0.6,
}

# W_recency: 时间衰减（指数衰减）
# 公式：w = e^(-ln(2) * days / half_life)
QUERY_HALF_LIFE = {
    'TECH_NEWS': 30,    # 科技新闻：30 天半衰期
    'RESEARCH': 180,    # 学术研究：180 天半衰期
    'FACTUAL': 730,     # 经典理论：2 年半衰期
}
```

---

### 3.3 Distributor 修改

**文件**: `backend/app/services/intelligence/court/distributor.py`

新增方法：
```python
async def summon_internet_witness(self, scout_queries: List[str]) -> Dict:
    """传唤联网证人"""
    return await self.internet_witness.summon(scout_queries)
```

---

### 3.4 Collector 修改

**文件**: `backend/app/services/intelligence/court/collector.py`

核心修改：
```python
async def collect_evidence(self, summoned_docs, query):
    # 1. Scout 拆解查询
    scout_queries = await self._scout(query)

    # 2. 并行：本地取证 + 联网取证
    local_tasks = [
        self._collect_local_doc(doc, query, scout_queries)
        for doc in summoned_docs
    ]
    internet_task = self.internet_witness.summon(scout_queries)

    # 3. 所有任务并行执行
    all_tasks = local_tasks + [internet_task]
    results = await asyncio.gather(*all_tasks, return_exceptions=True)
```

---

## 4. 配置项

### 4.1 .env 新增

```ini
# 联网搜索配置
TAVILY_API_KEY=tvly-dev-xxx
TAVILY_MAX_RESULTS=3
TAVILY_SEARCH_DEPTH=advanced
TAVILY_CONCURRENT_LIMIT=5
```

### 4.2 config.py 新增

```python
# V49.0 联网证人配置 (Tavily)
TAVILY_API_KEY: Optional[str] = None
TAVILY_MAX_RESULTS: int = 3
TAVILY_SEARCH_DEPTH: str = "advanced"
TAVILY_CONCURRENT_LIMIT: int = 5
```

---

## 5. 测试结果

### 5.1 单测

```bash
# InternetWitness 导入测试
✅ InternetWitness 导入成功

# Tavily API 调用测试
📡 [InternetWitness] 正在执行 1 个子查询...
✅ [InternetWitness] 检索到 3 条外部证据
```

### 5.2 完整法庭测试

**查询**: "信息安全中的加密方法有哪些？"

**证人列表**:
```
1. Galaxy_密码学_理论 → 87d2d2c2... (5 个证据分片)
2. Galaxy_Gfm → f3350f17... (3 个证据分片)
3. Galaxy_Algorithm → bbd90abf... (3 个证据分片)
4. Galaxy_Retrieval_Benchmarks → bcd1c05e... (3 个证据分片)
5. Galaxy_评估_Synthetic → 09b552ba... (3 个证据分片)
6. 互联网证人 → INTERNET... (3 个证据分片) ✅
```

**判决引用**:
```
【引用星系】['Galaxy_密码学_理论', '互联网证人']
【置信度】0.95
```

---

## 6. 文件清单

### 新建文件
| 文件 | 行数 | 描述 |
|------|------|------|
| `internet_witness.py` | ~200 | Tavily SDK 封装，动态置信度计算 |

### 修改文件
| 文件 | 修改内容 |
|------|----------|
| `distributor.py` | + 导入、+ 初始化、+ 新方法 |
| `collector.py` | + 导入、+ 初始化、重构 `collect_evidence` |
| `config.py` | +4 个 Tavily 配置项 |
| `.env` | +3 个 Tavily 配置 |

---

## 7. 待实现功能

### P3: 四色置信度系统
- 红（CRITICAL）: 证据冲突，需人工介入
- 黄（WARNING）: 单一来源，需交叉印证
- 蓝（VERIFIED）: 多来源一致，高置信度
- 绿（AUTHORITATIVE）: 权威来源 + 时间新鲜

### P3: CRUD 动态进化
- `ChunkRevision` 记录法庭裁决结论
- Git 备份修改历史
- 定期合并相似 Chunk

---

## 8. 成本估算

**Tavily API 成本**:
- 免费层：1,000 credits/月
- 按量付费：$0.008/credit
- 测试阶段：约 $1-2/月
- 生产阶段：约 $10-50/月（视请求量而定）

**优化建议**:
1. 设置 `TAVILY_CONCURRENT_LIMIT` 限制并发
2. 设置 `TAVILY_MAX_RESULTS` 限制返回数量
3. 仅在必要时调用（本地证据不足时）

---

## 9. 下一步行动

1. ✅ 联网证人核心功能完成
2. ⏳ 实现日志记录（当前）
3. ⏳ 四色置信度系统（用户思考中）
4. ⏳ CRUD 动态进化（用户思考中）

---

**记录人**: Claude Code  
**验证状态**: ✅ 测试通过  
**最后更新**: 2026-04-15
