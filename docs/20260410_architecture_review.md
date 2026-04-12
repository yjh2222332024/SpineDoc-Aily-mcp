# 架构审查日志 - 2026/04/10

## 会议主题：检索系统架构冲突分析

---

## 一、Navigator vs CascadingRetriever 冲突分析

### 1.1 现状：两套检索逻辑打架

**CascadingRetriever (泳道金字塔)** - `backend/app/services/rag/cascading_retriever.py`

```
工作流程:
1. TOC 语义撞击 → 找到相关章节范围 (limit=5)
2. 泳道融合 → 合并重叠/相邻页码范围
3. 泳道内检索 → 向量搜索 + 金字塔权重加成 (×3.5)
4. Reranker 精排 → 输出 Top-K 最终结果

特点:
- ✅ 一次性完成检索 + 重排
- ✅ 泳道权重加成 (落在命中的航道内内容 ×3.5)
- ✅ 兜底全局搜索 (航道内无匹配时切换)
- ❌ 没有多跳迭代能力
```

**Navigator (多跳搜索)** - `spine_cli/core/agents/navigator/nodes.py`

```
工作流程:
1. cartographer_node → 从 initial_hits 提取锚点 (铁锚策略：page>25 优先)
2. field_investigator_node → OCR 收割锚点周围页面 (±1 页扩展)
3. grader_critic_node → 判断是否足够 (page>=25 视为正文)
4. [不足] → rewriter_node → 重写查询 → 回到步骤 1 (最多 3 跳)
5. [充足] → editor_node → LLM 合成答案

特点:
- ✅ 多跳迭代 (最多 3 跳，动态重写查询)
- ✅ 铁锚策略 (优先 page > 25，避开目录区)
- ✅ 按需 OCR 收割 (只抓取关键页面)
- ❌ 依赖 initial_hits 质量
```

### 1.2 冲突点

#### 冲突 1：检索责任重叠

```python
# engine.py:196-200
# 先用 CascadingRetriever 做一轮检索
tasks = [cascading_retriever.retrieve(query=query, doc_id=d.id, ...) for d in docs]
all_results = await asyncio.gather(*tasks)
initial_hits = []
for r in all_results: initial_hits.extend(r)  # ← 已重排过的结果

# engine.py:215-216
# 然后把结果丢给 Navigator 再做一轮
state = {..., "initial_hits": initial_hits, ...}
res = await create_navigator_graph().ainvoke(state)
```

**问题**: CascadingRetriever 已经做了 **泳道筛选 + Reranker 精排**，Navigator 又基于这些结果再做一轮 **锚点提取 + OCR 收割** —— **重复劳动**！

#### 冲突 2：权重体系冲突

| 系统 | 权重策略 |
|------|----------|
| CascadingRetriever | 泳道内 × 3.5 + JIT 关键词 + Reranker |
| Navigator | 铁锚策略 (page > 25 优先) + 多跳迭代 |

**冲突场景**:
- CascadingRetriever 可能把 P15 (目录区) 的内容因为向量相似度高而排前面
- Navigator 的铁锚策略明确要 **避开 P25 以内**
- 两套规则互相矛盾！

#### 冲突 3：调用链冗余

```
用户 query
  ↓
CascadingRetriever.retrieve()  ← 第一层检索 (泳道 + 重排)
  ↓
initial_hits (已精排)
  ↓
Navigator 系统
  ├── cartographer_node  ← 从 initial_hits 提取锚点 (第二层筛选)
  ├── field_investigator_node  ← OCR 收割 (第三层)
  └── editor_node  ← LLM 合成 (第四层)
```

**结果**: 一个简单的检索任务被搞成了 **4 层流水线**，性能爆炸！

### 1.3 本质区别

| 维度 | CascadingRetriever | Navigator |
|------|-------------------|-----------|
| 设计目标 | **一次性精准检索** | **多跳迭代挖掘** |
| 适用场景 | 直接事实型问题 | 深度推理/多文档关联 |
| 检索策略 | 泳道约束 + 权重加成 | 锚点启发 + 动态重写 |
| 计算成本 | 低 (1 次向量搜索 + Rerank) | 高 (多轮 OCR + LLM) |

### 1.4 建议分工：EvidenceHarvester (原 CascadingRetriever)

**定位：卑微的机械装置 (Mechanism)**
> "机制应该是卑微的、确定性的、不带灵魂的。" —— Uncle Bob

**职责：**
- **数据分拣：** 它是系统的高性能感官。给定查询和 ISR 提供的航道，它必须在 100ms 内返回 Top-15 个切片。
- **职责剥离：** 严禁集成任何 LLM 状态、动态重排或复杂的业务逻辑。它只负责“召回（Recall）”。

**核心算法：**
- **Hybrid Search：** 向量搜索 (Dense Vector) 与 关键词搜索 (BM25) 双轨并行。
- **RRF 排名融合：** 废弃 `weight * 3.5` 魔法数字，采用 **Reciprocal Rank Fusion (RRF)** 算法进行无监督排名合并。
- **Contextual Indexing：** 利用入库期预计算的切片摘要进行语义对齐，提升机械匹配的精度。

### 1.5 改进方案：Navigator 3.0 计算图演进

**核心思想：** Navigator 不再是 Cascading 的“下游消费者”，而是整个 **Computation Graph (计算图)** 的主控节点。

1. **StructuralAnchorPolicy：** 废除 `page > 25`。强制解析 TOC 定位“第一章”或“正文”物理起始页作为主航道锚点。
2. **IEvidenceSource 接口隔离：** Navigator 通过抽象接口调用 EvidenceHarvester，确保策略逻辑与检索机制完全解耦。
3. **Speculative Execution：** 在多跳推理（Investigator）的同时，利用初步召回结果进行“预览版”答案生成，提升极速反馈。

---

## 二、联邦法庭系统局限性分析

### 2.1 系统架构

```
联邦法庭 (Federation) - 多文档/内外对比系统

entry_distributor_node (入场分发)
├── PDF 证人组 (witness_node) - 每文档一个证人
└── 市场证人 (quant_market_witness_node) - 外部实时数据
               ↓
moderator_node (主理人/法官)
├── Layer1: 物理页码对线 (同页不同说→冲突)
└── Layer2: LLM 语义冲突检测 (数值/事实矛盾)
               ↓
[CONFLICT] → cross_examination_node (交叉盘问)
          └── 携带原始证据回溯质询
          └── [CONFIRM]/[CORRECT] 二次确认
               ↓
[CONSENSUS] → integrator_node (首席大法官)
            └── 生成结构化判决书
            └── grounding_map (事实溯源)
```

### 2.2 核心节点职责

| 节点 | 职责 | 核心特点 |
|------|------|----------|
| entry_distributor_node | 并行拉起 PDF 证人 + 市场证人 | 按文档分组，同时取证 |
| witness_node | PDF 文档证人 | 负向约束：禁止总结/联想/外推 |
| quant_market_witness_node | 外部市场证人 | Finnhub 新闻 + DailyFX 日历 + Serper 搜索 |
| moderator_node | 冲突检测法官 | 分层检测：物理页码→语义冲突 |
| cross_examination_node | 交叉盘问 | 携带原始证据回溯质询 |
| integrator_node | 首席大法官 | 生成判决书 + grounding_map |

### 2.3 数据类型

```python
AtomicClaim:     # 原子论点
  - content: 事实描述
  - page: 物理页码
  - witness_id: 证人 ID
  - claim_type: FACT/OPINION/CONFLICT
  - confidence: 置信度

CollisionPoint:  # 冲突点
  - collision_type: PAGE_CONFLICT/VALUE_CONFLICT/LOGIC_GAP
  - description: 冲突描述
  - involved_witnesses: 涉事证人
  - severity: 严重程度 (0-1)
```

### 2.4 系统优势

1. **负向约束提示** - 证人节点明确禁止总结/联想/外推
2. **分层冲突检测** - 先用规则快速检测，再用 LLM 深度扫描
3. **回溯质询机制** - 携带原始证据进行二次确认，避免编造
4. **结构化判决** - 输出 grounding_map，每个事实可溯源
5. **外部证人集成** - 实时 API 数据作为独立证人参与辩论

### 2.5 局限性

#### 局限 1：与 CascadingRetriever 职责重叠

两者都负责检索，但 Federation 更侧重**对比场景**。当前调用链：

```python
# engine.py:197-208
# 先用 CascadingRetriever 对所有文档做检索
tasks = [cascading_retriever.retrieve(...) for d in docs]
all_results = await asyncio.gather(*tasks)
initial_hits = [...]

# 多文档/对比问题 → 走 Federation
if len(docs) > 1 or any(kw in query for kw in ["对比", "差异", "vs"]):
    state = create_initial_state(query, doc_ids, doc_paths)
    state["initial_hits"] = initial_hits  # ← 依赖 Cascading 的粗检索结果
    res = await create_federated_graph().ainvoke(state)
```

**问题**: Federation 的 `initial_hits` 完全依赖 CascadingRetriever，自身没有独立检索能力。

#### 局限 2：量化证人过于垂直

`quant_market_witness_node` 仅支持金融场景：
- Finnhub API → 个股新闻
- DailyFX API → 宏观经济日历
- Serper API → 谷歌新闻搜索

**通用场景无外部数据源**:
- 问："对比 Python 和 Go 的并发模型" → 无外部证人
- 问："这份技术报告与行业标准的差异" → 无外部证人

**建议**: 增加通用搜索证人 (如维基百科、学术论文 API)。

#### 局限 3：多跳能力弱于 Navigator

| 能力 | Federation | Navigator |
|------|------------|-----------|
| 多轮迭代 | 有 (辩论循环≤3) | 有 (最多 3 跳) |
| 查询重写 | 无 | 有 (rewriter_node) |
| 按需 OCR | 有 | 有 |
| 泳道约束 | 无 (依赖 initial_hits) | 可增强 |

**Federation 的迭代是被动的**：只有发现冲突时才进入交叉盘问，无法主动重写查询扩大搜索范围。

#### 局限 4：证人隔离导致上下文碎片化

每个 `witness_node` 只能看到**单个文档**的内容：

```python
# witness_node 的输入
context = "仅当前文档的片段"  # 无法看到其他文档
```

**问题**: 如果问题需要跨文档综合理解 (如"A 报告的第三章和 B 报告的第二章有什么关系")，单个证人无法回答。

### 2.6 改进建议

1. **明确分工**:
   - 简单问题 → CascadingRetriever 直接回答
   - 复杂/对比问题 → Federation 深度辩论

2. **增强 Federation 独立性**:
   - 在第一跳加入 TOC 泳道挖掘 (同 Navigator 改造方案)
   - 增加通用外部搜索证人 (维基百科/Google Scholar)

3. **增加跨文档综合节点**:
   ```
   [证人取证] → [跨文档综合官] → [主理人冲突检测]
   ```

---

## 三、下一步行动

### 3.1 优先级排序

1. **高优先级**: Navigator 吸收泳道挖掘逻辑 (减少调用链冗余)
2. **中优先级**: 明确 CascadingRetriever 和 Federation 的分工边界
3. **低优先级**: 增加 Federation 的通用外部搜索证人

### 3.2 待验证假设

- 假设：Navigator 的铁锚策略 (page>25) 对大部分文档有效
- 验证方法：统计不同类型文档的正文起始页码分布

- 假设：泳道约束能提高检索信噪比
- 验证方法：对比有/无泳道约束的检索结果质量

---

## 四、会议结论

**核心结论**:
1. CascadingRetriever 定位为"素材收割机"，负责广撒网召回
2. Navigator 定位为"精度提取器"，负责深度挖掘和多跳推理
3. Navigator 应吸收 Cascading 的泳道挖掘逻辑，但不是替代原有逻辑
4. Federation 系统适合多文档对比场景，但需增强独立检索能力

**一句话总结**: **CascadingRetriever 负责"找得到"，Navigator 负责"找得准"**

---

*记录时间：2026/04/10*
*记录者：AI Assistant*
