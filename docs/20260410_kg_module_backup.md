# KG 模块备份与未来规划 - 2026/04/10

## 会议主题：KGAdapter 备份至 backups 目录

---

## 一、KG 模块当前状态

### 1.1 目录结构

```
spine_cli/core/kg/
├── __init__.py       # 只有 1 行注释 "# KG Module"
└── adapter.py        # KGAdapter 类 (66 行代码)
```

### 1.2 核心能力

```python
class KGAdapter:
    """
    OpenKG 知识图谱适配器 (低成本版)
    职责：
    1. 实体对齐 (Entity Linking): 将章节标题映射到标准实体
    2. 知识扩写 (KG Expansion): 根据实体寻找关联概念
    """
    
    async def link_entities(self, titles: List[str]) -> Dict[str, List[str]]:
        """从章节标题中提取标准化学术实体"""
        # 例如："3.2 Transformer 架构" → ["Transformer"]
        
    async def get_concept_path(self, entity: str) -> List[str]:
        """获取概念层级路径"""
        # 例如："肺癌" → ["肺癌", "癌症", "疾病"]
```

### 1.3 依赖资源

| 资源 | 状态 | 位置 |
|------|------|------|
| `KG_ENTITY_LINKING_PROMPT` | ✅ 已定义 | `spine_cli/prompts/templates.py:698` |
| `KGAdapter` 类 | ✅ 完整 | `spine_cli/core/kg/adapter.py` |
| 外部 API | ❌ 无 | 纯 LLM 模拟，零配置 |

---

## 二、使用情况分析

### 2.1 引用检查

| 检查项 | 结果 |
|--------|------|
| `spine_cli/core/engine.py` 引用 | ❌ 无 |
| `spine_cli/core/` 其他文件引用 | ❌ 无 |
| `spine_cli/` 其他文件引用 | ❌ 无 |
| `backend/` 引用 | ❌ 无 |

### 2.2 结论

**❌ 没有整合进主逻辑！**

- 是一个**预留的扩展点**
- 代码完整可运行，但无调用方
- Prompt 已定义但未被使用

---

## 三、未来整合场景设计

### 场景 A: TOC 语义增强 (优先级：中)

**整合点**: `backend/app/services/toc/manager.py`

```python
from spine_cli.core.kg.adapter import KGAdapter

class TOCManager:
    async def enrich_with_kg(self, toc_items: List[Dict]) -> List[Dict]:
        """使用 KG 适配器增强 TOC 语义信息"""
        adapter = KGAdapter()
        titles = [item["title"] for item in toc_items]
        
        # 1. 实体对齐
        entities = await adapter.link_entities(titles)
        
        # 2. 概念路径扩写
        concept_paths = {}
        all_entities = set()
        for entity_list in entities.values():
            all_entities.update(entity_list)
        
        for entity in all_entities:
            concept_paths[entity] = await adapter.get_concept_path(entity)
        
        # 3. 注入到 TocItem
        for item in toc_items:
            item["kg_entities"] = entities.get(item["title"], [])
            item["concept_paths"] = {
                e: concept_paths.get(e, []) 
                for e in entities.get(item["title"], [])
            }
        
        return toc_items
```

**收益**:
- 检索时支持实体级查询扩展
- 示例：搜 "注意力机制" → 关联到 "Transformer" 章节

---

### 场景 B: 检索查询扩展 (优先级：低)

**整合点**: `backend/app/services/rag/cascading_retriever.py`

```python
from spine_cli.core.kg.adapter import KGAdapter

class CascadingRetriever:
    async def retrieve(self, query: str, ...):
        # 1. KG 实体提取
        adapter = KGAdapter()
        entities = await adapter.link_entities([query])
        
        # 2. 概念路径扩展
        expanded_queries = [query]
        for entity_list in entities.values():
            for entity in entity_list:
                path = await adapter.get_concept_path(entity)
                expanded_queries.extend(path)
        
        # 3. 多查询混合检索
        all_results = []
        for q in set(expanded_queries):
            results = await vector_store.search(query=q, ...)
            all_results.extend(results)
        
        # 4. 去重 + Rerank
        return await reranker.rerank(query, all_results, top_k=limit)
```

**收益**:
- 提升召回率，尤其是跨领域查询
- 示例：搜 "肿瘤治疗" → 扩展到 "癌症" → "疾病" 层级

---

### 场景 C: Chunk 索引时 KG 注入 (优先级：低)

**整合点**: `backend/app/services/rag/logic_refiner.py`

```python
from spine_cli.core.kg.adapter import KGAdapter

class LogicRefiner:
    async def refine_batch(self, doc_title, toc_items, segments, ...):
        # 1. 提取章节 KG 实体
        adapter = KGAdapter()
        kg_entities = await adapter.link_entities(
            [item["title"] for item in toc_items]
        )
        
        # 2. 为每个 Chunk 注入 KG 标签
        for seg in segments:
            chapter_entities = kg_entities.get(seg["breadcrumb"], [])
            seg["metadata_json"]["kg_entities"] = chapter_entities
        
        return refined_chunks
```

**收益**:
- Chunk 索引携带语义实体
- 支持实体级过滤和聚合

---

## 四、整合决策

### 4.1 当前建议：暂时备份，等待明确场景

**理由**:
1. 当前 RAG 流水线已稳定运行
2. KG 增量的价值未经验证
3. 增加复杂度和 API 调用成本
4. 等 Phase 1-3 (模型重构、算法迁移、检索优化) 完成后再评估

### 4.2 未来触发条件

当以下情况出现时，考虑恢复 KG 模块：

- [ ] 用户反馈检索召回率不足
- [ ] 需要跨文档语义关联
- [ ] 需要实体级统计/分析功能
- [ ] 要构建知识图谱可视化功能

---

## 五、备份操作

### 5.1 执行命令

```bash
# 复制 KG 模块到 backups
cp -r spine_cli/core/kg/ backups/kg_module/

# 删除原目录
rm -rf spine_cli/core/kg/
```

### 5.2 恢复方式

```bash
# 需要时从 backups 恢复
cp -r backups/kg_module/ spine_cli/core/kg/
```

---

## 六、待办任务清单

| 任务 | 优先级 | 状态 |
|------|--------|------|
| 备份 KG 模块到 backups | 高 | ⏳ 待执行 |
| 删除原 `spine_cli/core/kg/` 目录 | 高 | ⏳ 待执行 |
| 更新架构文档记录 KG 模块位置 | 低 | ⏳ 待执行 |
| 未来评估 KG 整合场景 | 低 | ⏳ 待定 |

---

## 七、相关文件

- KG Adapter 源码：`backups/kg_module/adapter.py`
- KG Prompt 模板：`spine_cli/prompts/templates.py:698`
- 相关讨论：`docs/20260410_architecture_refactor_plan.md`

---

*记录时间：2026/04/10*
*记录者：AI Assistant*
*状态：备份待执行*
