# 🏛️ 架构重构计划 (Uncle Bob 审计版)

**审计日期**: 2026-04-15  
**审计人**: Uncle Bob (50 年编程经验视角)  
**项目状态**: ⚠️ 功能完整，工程纪律需加强  

---

## 1. 文件价值与冗余审计

### 1.1 严重：逻辑分裂

| 文件对 | 问题 | 建议 |
|--------|------|------|
| `color_confidence.py` vs `unified_confidence.py` | 两者都在算置信度，但算法模型不统一（一个用 0.65 做绿色阈值，一个用 0.70） | 合并。保留 `UnifiedConfidenceCalculator` 作为唯一入口，将 `ColorConfidenceCalculator` 降级为它的底层数学引擎 |

### 1.2 严重：基础架构泄露

| 文件 | 问题 | 建议 |
|------|------|------|
| `config_loader.py` | 潜伏在 `services/intelligence/court/` 里，这叫"基础架构泄露"。配置加载是全系统的基石，不应属于某个特定业务模块 | 挪到 `backend/app/core/config_loader.py` |

### 1.3 严重：上帝类 (God Object)

| 文件 | 问题 | 建议 |
|------|------|------|
| `spine_engine.py` | 既管解析、管 OCR、管索引，现在还要管 Git 提交和冲突代谢 | 立即提取 `MetabolismManager`。让 `SpineEngine` 只负责编排，把"怎么写 Git"和"怎么更新数据库"丢给代谢经理 |

---

## 2. 降级逻辑薄弱环节

### 2.1 Distributor 全量兜底风险

**现状**:
```python
# 如果找不到聚类，select(Galaxy.id) 召回全量星系
```

**风险**: 如果 1000 个星系，这行代码能让 LLM 账单爆炸，或直接让数据库连接池瘫痪

**改进**: 兜底必须带 `LIMIT`，或者降级为"最近活跃星系"

```python
# 改进后
stmt = select(Galaxy).where(...).limit(50)  # 限制最大召回数
```

### 2.2 ThesaurusManager 单点故障

**现状**: 如果 `thesaurus_map.json` 损坏，直接返回空字典

**风险**: 导致 Distributor 每次都走全量召回

**改进**: 应该有"内置硬编码基础映射"作为最后一道防线

```python
DEFAULT_THESAURUS = {
    "RAG": ["retrieval", "augmentation", "generation"],
    "AI": ["artificial", "intelligence", "机器学习"]
}
```

### 2.3 InternetWitness 并发漏洞

**现状**: 信号量 (Semaphore) 锁住了整个 `summon` 函数

**风险**: 一次只能有一个用户传唤联网证人

**改进**: 信号量应该锁住内部的单个 HTTP 请求，而不是整个批处理函数

```python
# 当前（错误）
async with self._semaphore:
    results = await asyncio.gather(*tasks)

# 改进（正确）
async def _search_single(query):
    async with self._semaphore:  # 锁住单个请求
        return await self._do_search(query)
```

---

## 3. 硬编码与配置整合清单

| 变量名 | 当前状态 | 改进方向 |
|--------|----------|----------|
| Scout 拆解数 | 硬编码为 3 | 移至 `settings.SCOUT_QUERY_LIMIT` |
| 证据颜色阈值 | 分散在两个 Python 文件里 | 统一整合进 `confidence_config.json` |
| 置信度半衰期 | 写死在 `color_confidence.py` | 移至 `settings` 或外部 JSON |
| TOC 限制数 | 提示词里写死 `toc[:50]` | 移至 `settings.CONTEXT_TOC_LIMIT` |
| 权威分加成 | `base * 1.10` 写在代码里 | 建立 `logic_weights.json` 统一管理 |

---

## 4. 架构重构指令 (The Master's Directive)

### 4.1 单例化 (Singletonize)

**问题**: `ThesaurusManager` 和 `InternetWitness` 不要在每个函数里都 `__init__` 一次

**风险**: 频繁读取 JSON 文件是极其不专业的 IO 浪费

**改进**:
```python
# 全局单例
_global_thesaurus: Optional[ThesaurusManager] = None

def get_thesaurus_manager() -> ThesaurusManager:
    global _global_thesaurus
    if _global_thesaurus is None:
        _global_thesaurus = ThesaurusManager()
    return _global_thesaurus
```

### 4.2 异步节流 (Rate Limiting)

**问题**: 在 `Distributor` 中引入 `Semaphore`

**改进**: 如果用户问了一个能触发 50 个文档的问题，必须按 5 个一组慢慢跑

```python
class Distributor:
    def __init__(self):
        self._semaphore = asyncio.Semaphore(5)  # 最多并发传唤 5 个证人

    async def summon_witnesses(self, ...):
        async with self._semaphore:
            # ...
```

### 4.3 提取代谢层 (Extract Metabolism)

**问题**: `moderator.py` 里的 `_identify_knowledge_delta` 混肴了"裁决"和"执行"

**改进**: 创建 `MetabolismService` 来接收裁决并执行物理操作

```
┌─────────────────────┐
│   Moderator (法官)   │ → 只负责判
└──────────┬──────────┘
           │ 判决书
           ▼
┌─────────────────────┐
│ MetabolismService   │ → 只负责执行
│ (执行书记官)        │   - 写 Git
│                     │   - 更新数据库
└─────────────────────┘
```

---

## 5. 执行优先级

### P0: 立即修复 (阻断性问题)
- [ ] 修复 `state` 未定义的 Bug（保住法庭能开庭）
- [ ] `Distributor` 兜底查询加 `LIMIT`

### P1: 高优先级 (影响稳定性)
- [ ] 提取 `MetabolismManager`
- [ ] `InternetWitness` 信号量修正（锁单个请求）
- [ ] `ThesaurusManager` 添加硬编码兜底映射

### P2: 中优先级 (影响可维护性)
- [ ] 合并 `color_confidence.py` 和 `unified_confidence.py`
- [ ] 移动 `config_loader.py` 到 `core/`
- [ ] 硬编码值迁移到配置

### P3: 低优先级 (工程纪律)
- [ ] `SpineEngine` 瘦身（职责分离）
- [ ] 全局单例化 (`ThesaurusManager`, `InternetWitness`)
- [ ] `Distributor` 并发节流

---

## 6. 修改记录

| 日期 | 修改内容 | 修改人 |
|------|----------|--------|
| 2026-04-15 | 初始版本（Uncle Bob 审计） | Claude Code |

---

**架构健康度**: ⭐⭐⭐ (3.5/5.0)  
**核心评价**: 逻辑非常漂亮，但工程纪律需要加强
