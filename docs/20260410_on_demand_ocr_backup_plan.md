# On-Demand OCR Enhancer 备份与未来整合规划 - 2026/04/10

## 会议主题：按需 OCR 补全功能备份至 backups 目录

---

## 一、模块当前状态

### 1.1 文件信息

```
backend/app/services/rag/on_demand_ocr.py
├── OnDemandOCREnhancer 类 (58 行)
└── get_enhancer() 工厂函数
```

### 1.2 核心能力

```python
class OnDemandOCREnhancer:
    """
    V17.0 结构化补全版
    职责：对内容缺失或公式密集的 Chunk 进行即时结构化重炼
    架构：全面接入 GLM-OCR 0.9B，输出高质量 Markdown
    """
    
    async def enhance_chunks(self, chunks, doc, force_ocr=False):
        # 1. 发现空洞分块 (内容 < 10 字符)
        # 2. 使用 GLMWorker.ocr_to_markdown() 重新渲染
        # 3. 替换原内容，标记为 [GLM-Enhanced]
```

### 1.3 依赖关系

| 依赖 | 状态 | 用途 |
|------|------|------|
| `GLMWorker` | ✅ 有用 | 被 `ocr_process_utils.py` 调用 |
| `fitz` (PyMuPDF) | ✅ 有用 | 渲染页面为图像 |
| `numpy` | ✅ 有用 | 图像处理 |

---

## 二、使用情况分析

### 2.1 引用检查

| 检查项 | 结果 |
|--------|------|
| `get_enhancer()` 被调用 | ✅ 是 (`cascading_retriever.py:24`) |
| `enhance_chunks()` 被调用 | ❌ **否** (无任何调用方) |
| `self.enhancer` 被使用 | ❌ **否** (初始化后从未调用) |

### 2.2 当前调用链

```
CascadingRetriever.__init__()
  ↓
self.enhancer = get_enhancer()  ← 初始化了
  ↓
❌ 从未在任何方法中调用 self.enhancer.enhance_chunks()
```

---

## 三、设计意图

### 3.1 原始设计

```
检索到 Chunk → 发现内容空洞 → 触发 OCR 补全 → 返回高质量内容
```

### 3.2 工作流程

```
1. CascadingRetriever.retrieve() 检索到 Chunk 列表
           ↓
2. 检测空洞分块 (content < 10 字符)
           ↓
3. 触发 OnDemandOCREnhancer.enhance_chunks()
           ↓
4. GLMWorker.ocr_to_markdown() 重新渲染页面
           ↓
5. 替换原内容，标记为 [GLM-Enhanced]
           ↓
6. 返回高质量补全后的 Chunk
```

### 3.3 适用场景

| 场景 | 描述 | 示例 |
|------|------|------|
| **扫描件 PDF** | 无文本层，纯图片 | 老教材、老论文 |
| **公式密集型** | 数学公式无法用文本表示 | 物理论文、数学教材 |
| **表格密集型** | 表格结构复杂 | 财务报表、实验数据 |
| **低质量 OCR** | 原文识别质量差 | 模糊扫描、手写注释 |

---

## 四、问题诊断

### 4.1 为什么没有被调用？

**可能原因**:
1. **性能考虑**: OCR 补全耗时较长，默认关闭
2. **场景有限**: 大部分文档有文本层，不需要补全
3. **成本考虑**: GLM-OCR 调用需要 GPU 资源
4. **整合未完成**: 设计时预留，未来整合

### 4.2 当前代码问题

**`cascading_retriever.py`**:
```python
class CascadingRetriever:
    def __init__(self, router, reranker):
        self.router = router
        self.reranker = reranker
        self.enhancer = get_enhancer()  # ← 初始化了，但没用
```

**需要添加调用逻辑**:
```python
async def retrieve(self, query, doc_id, limit, page_ranges):
    # ... 现有检索逻辑 ...
    
    # 🆕 按需 OCR 补全 (可选)
    if need_enhance:
        results = await self.enhancer.enhance_chunks(results, doc, force_ocr=False)
    
    # Reranker 精排
    final_results = await self.reranker.rerank(query, results, top_k=limit)
    return final_results
```

---

## 五、未来整合方案

### 5.1 方案 A: 作为可选增强开关 (优先级：中)

**修改 `CascadingRetriever`**:

```python
class CascadingRetriever:
    def __init__(self, router, reranker, enable_enhance=False):
        self.router = router
        self.reranker = reranker
        self.enable_enhance = enable_enhance
        self.enhancer = get_enhancer() if enable_enhance else None
    
    async def retrieve(self, query, doc_id, limit, page_ranges, enhance=False):
        # ... 现有检索逻辑 ...
        
        # 🆕 按需 OCR 补全
        if enhance and self.enhancer:
            results = await self.enhancer.enhance_chunks(results, doc, force_ocr=False)
        
        # Reranker 精排
        final_results = await self.reranker.rerank(query, results, top_k=limit)
        return final_results
```

**调用方控制**:
```python
# engine.py
cascading_retriever = CascadingRetriever(router=router, reranker=reranker, enable_enhance=True)

# 检索时按需启用
results = await cascading_retriever.retrieve(query, doc_id, limit=15, enhance=True)
```

---

### 5.2 方案 B: 智能触发 (优先级：低)

**自动检测需要补全的场景**:

```python
async def retrieve(self, query, doc_id, limit, page_ranges):
    # ... 现有检索逻辑 ...
    
    # 🆕 智能检测
    empty_chunks = [c for c in results if len(c.get('content', '')) < 50]
    if empty_chunks and doc.is_scanned:
        print(f"🔍 检测到 {len(empty_chunks)} 个空洞分块，触发 OCR 补全...")
        results = await self.enhancer.enhance_chunks(results, doc)
    
    # Reranker 精排
    ...
```

---

### 5.3 方案 C: 专用 API (优先级：低)

**提供独立的增强接口**:

```python
# engine.py
async def enhance_chunks(self, chunk_ids: List[str], force_ocr: bool = False):
    """对指定 Chunk 进行 OCR 补全"""
    async with self._session_maker() as session:
        chunks = await session.get(Chunk, chunk_ids)
        doc = await session.get(Document, chunks[0].document_id)
        
        with fitz.open(doc.file_path) as doc_obj:
            enhancer = get_enhancer()
            chunk_dicts = [c.to_dict() for c in chunks]
            enhanced = await enhancer.enhance_chunks(chunk_dicts, doc_obj, force_ocr)
            
            # 回填数据库
            for e in enhanced:
                chunk = await session.get(Chunk, e['id'])
                chunk.content = e['content']
            await session.commit()
```

---

## 六、整合决策

### 6.1 当前建议：暂时备份，等待明确场景

**理由**:
1. 当前 RAG 流水线已稳定运行
2. 大部分文档有文本层，不需要 OCR 补全
3. 增加复杂度和服务延迟
4. 等 Phase 1-3 完成后再评估是否需要

### 6.2 未来触发条件

当以下情况出现时，考虑恢复 OCR Enhancer 模块：

- [ ] 用户反馈扫描件文档检索质量差
- [ ] 需要处理公式/表格密集型文档
- [ ] 检测到大量空洞 Chunk (content < 50 字符)
- [ ] 需要高精度公式识别场景

---

## 七、备份操作

### 7.1 执行命令

```bash
# 复制到 backups
cp backend/app/services/rag/on_demand_ocr.py backups/

# 清理 cascading_retriever.py 中的闲置引用
# 删除:
#   from app.services.rag.on_demand_ocr import get_enhancer
#   self.enhancer = get_enhancer()
```

### 7.2 恢复方式

```bash
# 需要时从 backups 恢复
cp backups/on_demand_ocr.py backend/app/services/rag/

# 恢复 cascading_retriever.py 中的引用
```

---

## 八、待办任务清单

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 备份 `on_demand_ocr.py` 到 backups | 高 | ⏳ 待执行 |
| 清理 `cascading_retriever.py` 中的闲置引用 | 高 | ⏳ 待执行 |
| 更新架构文档记录备份位置 | 低 | ⏳ 待执行 |
| 未来评估 OCR Enhancer 整合场景 | 低 | ⏳ 待定 |

---

## 九、相关文件

- 备份位置：`backups/on_demand_ocr.py`
- 调用方：`backend/app/services/rag/cascading_retriever.py`
- 依赖模块：`backend/app/services/ocr/glm_worker.py` (有用，保留)
- 相关讨论：`docs/20260410_architecture_refactor_plan.md`

---

## 十、恢复示例代码

### 未来整合到 CascadingRetriever

```python
# backend/app/services/rag/cascading_retriever.py

class CascadingRetriever:
    def __init__(self, router, reranker, enable_enhance=False):
        self.router = router
        self.reranker = reranker
        self.enable_enhance = enable_enhance
        if enable_enhance:
            from .on_demand_ocr import get_enhancer
            self.enhancer = get_enhancer()
    
    async def retrieve(self, query, doc_id, vector_store, limit=5, 
                       page_ranges=None, enhance=False):
        # 1. TOC 语义撞击
        # 2. 泳道融合
        # 3. 集群航道内检索
        results = await vector_store.search(...)
        
        if not results:
            return []
        
        # 🆕 4. 按需 OCR 补全
        if enhance and self.enable_enhance:
            # 需要打开 fitz.Document
            doc = await self._get_document(doc_id)
            with fitz.open(doc.file_path) as doc_obj:
                results = await self.enhancer.enhance_chunks(
                    results, doc_obj, force_ocr=False
                )
        
        # 5. Reranker 精排
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        final_results = await self.reranker.rerank(
            query, results[:limit * 3], top_k=limit
        )
        
        return final_results
    
    async def _get_document(self, doc_id):
        """获取文档记录"""
        async with self._session_maker() as session:
            return await session.get(Document, UUID(doc_id))
```

---

*记录时间：2026/04/10*
*记录者：AI Assistant*
*状态：备份待执行*
