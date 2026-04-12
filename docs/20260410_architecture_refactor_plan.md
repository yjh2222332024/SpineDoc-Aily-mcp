# 架构重构规划 - 2026/04/10

## 会议主题：Chunk 元数据瘦身与 TOC 职责归位

---

## 一、核心设计思想

### Chunk 定位：最小化检索原子单元

```
Chunk = 检索引擎的"元数据"，不是知识载体

设计原则:
- ✅ 只存储检索必需的最小字段
- ✅ 通过 toc_item_id 回溯父节点获取完整上下文
- ✅ 避免 SLM 上下文爆炸
```

### TOC 定位：章节原单元 (Chunk 的容器)

```
TocItem = Chunk 的父节点/容器

设计原则:
- ✅ 存储章节级元数据 (summary, logic_tags, causality_links)
- ✅ 支持层级回溯 (Chunk → TocItem → Parent TocItem → ...)
- ✅ 航道检索时动态加载元数据，非检索时不占用上下文
```

---

## 二、当前问题分析

### 2.1 Chunk 元数据冗余

**当前模型 (`backend/app/core/models.py`)**:

```python
class Chunk(SQLModel, table=True):
    content: str
    page_number: int
    breadcrumb: Optional[str]          # ❌ 冗余
    embedding: List[float]
    toc_item_id: Optional[UUID]        # ✅ 已有外键
    document_id: UUID
    level: int                         # ❌ 冗余 (TocItem 已有)
    metadata_json: Optional[Dict]      # ⚠️ 可能过大
    logic_tags: Optional[List[str]]    # ❌ 应该属于 TocItem
    causality_links: Optional[Dict]    # ❌ 应该属于 TocItem
    confidence_score: float
```

**问题**:
1. `breadcrumb` 与 `toc_item_id` 功能重叠
2. `level` 在 Chunk 和 TocItem 中重复存储
3. `logic_tags` 和 `causality_links` 撑爆 SLM 上下文
4. 检索时每个 Chunk 都携带大量冗余元数据

---

### 2.2 栈式算法职责错位

**当前所在**: `backend/app/services/rag/splitter.py:76-96`

```python
# splitter.py:split_by_toc()
stack = []
for item in toc_items:
    current_level = int(item.get("level", 1))
    p_start = int(item.get("physical_page", item.get("page", 1)))
    
    while stack and stack[-1].get("level", 1) >= current_level:
        closed_item = stack.pop()
        closed_item["physical_end"] = p_start - 1
    
    item["physical_start"] = p_start
    stack.append(item)

while stack:
    remaining = stack.pop()
    remaining["physical_end"] = total_pages
```

**问题**: **TOC 的区间计算逻辑跑到了 RAG 分片器里面！**

---

### 2.3 TOC 后处理逻辑分散

| 逻辑 | 当前所在 | 应该所在 |
|------|----------|----------|
| 栈式区间计算 | ❌ splitter.py | ✅ toc/manager.py |
| Offset 计算 | ✅ toc/aligner.py | ✅ toc/aligner.py |
| 父子关系建树 | ✅ toc/manager.py | ✅ toc/manager.py |
| 质量验证 | ✅ toc/validator_rules.py | ✅ toc/validator_rules.py |
| 物理聚类 | ✅ toc/clustering.py | ✅ toc/clustering.py |

---

## 三、重构方案

### 3.1 Chunk 模型瘦身

**重构后的 Chunk 模型**:

```python
class Chunk(SQLModel, table=True):
    """
    最小化检索原子单元
    
    设计原则:
    - 只存储检索必需的字段
    - 通过 toc_item_id 回溯父节点获取完整上下文
    - 避免 SLM 上下文爆炸
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # === 检索必需字段 ===
    content: str                         # 内容本身
    page_number: int                     # 物理页码 (用于标注)
    embedding: List[float] = Field(      # 向量 (用于检索)
        sa_column=Column(Vector(settings.EMBEDDING_DIMENSION))
    )
    
    # === 关联字段 ===
    toc_item_id: UUID = Field(           # 指向"小节原单元"
        foreign_key="tocitem.id", ondelete="SET NULL"
    )
    document_id: UUID = Field(           # 文档 ID (用于快速筛选)
        foreign_key="document.id", ondelete="CASCADE"
    )
    
    # === 可选：轻量级元数据 ===
    # 只保留检索时快速筛选需要的字段
    # 复杂元数据应存储在 TocItem 中
```

**迁移逻辑**:
- `breadcrumb` → 删除 (通过 `toc_item_id` 实时计算)
- `level` → 删除 (从 TocItem 继承)
- `logic_tags` → 迁移到 TocItem
- `causality_links` → 迁移到 TocItem
- `metadata_json` → 精简为 `{"ocr_confidence": float, "has_table": bool, "has_formula": bool}`

---

### 3.2 TocItem 模型增强

**重构后的 TocItem 模型**:

```python
class TocItem(SQLModel, table=True):
    """
    章节原单元 (Chunk 的容器)
    
    设计原则:
    - 存储章节级元数据
    - 支持 Chunk 回溯获取完整上下文
    - SLM 调用时从此处加载元数据
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    
    # === 基础信息 ===
    title: str
    level: int
    page: int                    # 逻辑页码
    physical_start: int          # 物理起始页
    physical_end: int            # 物理结束页
    
    # === 语义增强 ===
    summary: Optional[str]       # LLM 生成的章节综述
    keywords: Optional[List[str]] = Field(sa_column=Column(JSON))
    
    # === 向量检索 ===
    embedding: Optional[List[float]] = Field(
        sa_column=Column(Vector(settings.EMBEDDING_DIMENSION))
    )
    keyword_embedding: Optional[List[float]] = Field(
        sa_column=Column(Vector(settings.EMBEDDING_DIMENSION))
    )
    
    # === 逻辑标签 (从 Chunk 迁移过来) ===
    logic_tags: Optional[List[str]] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    causality_links: Optional[Dict[str, Any]] = Field(
        default_factory=dict, sa_column=Column(JSON)
    )
    
    # === 层级关系 ===
    parent_id: Optional[UUID] = Field(foreign_key="tocitem.id")
    document_id: UUID = Field(foreign_key="document.id")
    
    # Relationships
    parent: Optional["TocItem"] = Relationship(...)
    children: List["TocItem"] = Relationship(...)
    chunks: List["Chunk"] = Relationship(...)  # 🆕 反向关联 Chunk
```

---

### 3.3 栈式算法迁移

**目标**: 将 `splitter.py` 中的栈式算法迁移到 `toc/manager.py`

**迁移前 (`splitter.py`)**:
```python
async def split_by_toc(self, doc, toc_items: List[Dict], ...):
    # ❌ 这里计算区间
    stack = []
    for item in toc_items:
        current_level = int(item.get("level", 1))
        p_start = int(item.get("physical_page", item.get("page", 1)))
        
        while stack and stack[-1].get("level", 1) >= current_level:
            closed_item = stack.pop()
            closed_item["physical_end"] = p_start - 1
        
        item["physical_start"] = p_start
        stack.append(item)
    
    while stack:
        remaining = stack.pop()
        remaining["physical_end"] = total_pages
    
    # 然后按区间切分...
```

**迁移后 (`toc/manager.py`)**:
```python
class TOCManager:
    def calculate_ranges(self, toc_items: List[Dict], total_pages: int) -> List[Dict]:
        """
        栈式算法计算物理区间 [physical_start, physical_end]
        
        工业标准实现，支持任意层级嵌套。
        """
        stack = []
        sorted_items = sorted(toc_items, key=lambda x: x.get("physical_page", 0))
        
        for item in sorted_items:
            current_level = int(item.get("level", 1))
            p_start = int(item.get("physical_page", 1))
            
            # 弹出所有同级/更高级 → 设置它们的结束页
            while stack and stack[-1].get("level", 1) >= current_level:
                closed_item = stack.pop()
                closed_item["physical_end"] = p_start - 1
            
            # 当前章节
            item["physical_start"] = p_start
            stack.append(item)
        
        # 最后剩下的全部到最后一页
        while stack:
            remaining = stack.pop()
            remaining["physical_end"] = total_pages
        
        return sorted_items
```

**迁移后 (`splitter.py`)**:
```python
async def split_by_toc(self, doc, toc_items: List[Dict], ...):
    """
    按 TOC 逻辑区间分片
    
    假设：toc_items 已经由 TOCManager.calculate_ranges() 计算好区间
    """
    # ✅ 直接使用已计算好的区间
    for item in toc_items:
        p_start = item["physical_start"]  # ← TOCManager 已计算好
        p_end = item["physical_end"]
        
        # 收集文本、调用语义切片、输出 Chunk
        ...
```

---

## 四、检索流程优化

### 当前流程 (冗余)

```
1. 向量检索 → Chunk (带 breadcrumb, logic_tags, metadata_json...)
   ↓
2. 把所有字段塞进 SLM 上下文
   ↓
3. SLM 处理超长上下文 → 可能截断/遗忘关键信息
```

### 优化后流程 (精简)

```
1. 向量检索 → Chunk (只有 content, page, toc_item_id)
   ↓
2. 按需加载元数据:
   - SELECT title, level FROM TocItem WHERE id = chunk.toc_item_id
   - SELECT logic_tags FROM TocItem WHERE id = chunk.toc_item_id
   ↓
3. SLM 看到精简后的上下文:
   "问题：XXX
    相关章节：第三章 第三节 (P20-P30)
    证据：[content...]"
```

---

## 五、待办任务清单

### Phase 1: 模型重构 (优先级：高)

- [ ] 修改 `Chunk` 模型，删除冗余字段
- [ ] 修改 `TocItem` 模型，迁移 `logic_tags` 和 `causality_links`
- [ ] 编写数据库迁移脚本 (Alembic)
- [ ] 更新 `LogicRefiner.refine_batch()` 输出逻辑

### Phase 2: 栈式算法迁移 (优先级：高)

- [ ] 在 `toc/manager.py` 中添加 `calculate_ranges()` 方法
- [ ] 修改 `splitter.py` 调用 `TOCManager.calculate_ranges()`
- [ ] 删除 `splitter.py` 中的栈式算法代码
- [ ] 更新单元测试

### Phase 3: 检索流程优化 (优先级：中)

- [ ] 修改 `CascadingRetriever` 按需加载元数据
- [ ] 修改 `Navigator` 和 `Federation` 的上下文构建逻辑
- [ ] 优化 SLM Prompt 模板，适配精简后的元数据

### Phase 4: 清理死代码 (优先级：低)

- [ ] 删除 `splitter.py` 中的 `MarkdownSplitter` 类
- [ ] 删除 `splitter.py` 中的 `markdown_splitter` 单例
- [ ] 清理未使用的导入语句

---

## 六、预期收益

| 维度 | 重构前 | 重构后 | 改善 |
|------|--------|--------|------|
| Chunk 表字段数 | 10+ | 6 | ⬇️ 40% |
| SLM 上下文长度 | ~2000 tokens | ~500 tokens | ⬇️ 75% |
| 检索响应时间 | ~150ms | ~80ms | ⬆️ 47% |
| 代码职责清晰度 | 中 | 高 | ⬆️ 显著 |

---

## 七、风险与缓解

### 风险 1: 数据库迁移导致数据丢失

**缓解措施**:
- 编写回滚脚本
- 先在测试环境验证
- 备份生产数据

### 风险 2: 现有调用链断裂

**缓解措施**:
- 逐步迁移，保持向后兼容
- 添加弃用警告 (Deprecation Warning)
- 更新所有测试用例

### 风险 3: 按需加载增加查询次数

**缓解措施**:
- 使用 JOIN 预加载 TocItem
- 添加缓存层 (Redis)
- 批量加载 (IN 查询)

---

## 八、时间估算

| Phase | 预估工时 | 依赖 |
|-------|----------|------|
| Phase 1: 模型重构 | 4 小时 | 无 |
| Phase 2: 算法迁移 | 3 小时 | Phase 1 |
| Phase 3: 检索优化 | 4 小时 | Phase 1, 2 |
| Phase 4: 清理死代码 | 1 小时 | Phase 1-3 |
| **总计** | **12 小时** | - |

---

## 九、验收标准

### Phase 1 验收
- [ ] 数据库迁移脚本成功执行
- [ ] 新旧数据对比一致
- [ ] 所有 CRUD 操作正常

### Phase 2 验收
- [ ] 栈式算法单元测试通过
- [ ] 边界情况测试通过 (空 TOC、单章节、深层嵌套)
- [ ] 性能基准测试通过

### Phase 3 验收
- [ ] 检索精度无下降
- [ ] SLM 上下文长度减少 50%+
- [ ] 端到端响应时间无退化

### Phase 4 验收
- [ ] 无死代码警告
- [ ] 代码覆盖率保持 80%+

---

*记录时间：2026/04/10*
*记录者：AI Assistant*
*状态：规划阶段，待执行*
