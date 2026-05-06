# 📜 联邦法庭实现日志 (2026-04-15)

## 1. 实现概览

**时间**: 2026-04-15  
**状态**: ✅ 核心功能完成，测试通过  
**测试查询**: "信息安全中的加密方法有哪些？"

---

## 2. 已实现的核心组件

### 2.1 法庭状态契约
**文件**: `backend/app/services/intelligence/court/state.py`

定义了联邦法庭的状态结构：
- `EvidencePackage`: 证据包（单个证人文档提供的全部证据）
- `EvidenceChunk`: 证据分片（冲突分析和裁决的基本单位）
- `ConflictItem`: 冲突点（大法官需要裁决的逻辑矛盾）
- `CourtState`: 法庭状态契约

关键设计决策：
- **证据分片是裁决的基本单位**，而非证词
- 多文档场景下，绕过 Integrator，直接返回证据分片供 Moderator 裁决

---

### 2.2 传唤官 (Distributor)
**文件**: `backend/app/services/intelligence/court/distributor.py`

职责：
1. 读取 ThesaurusMap，找到 query 相关的 cluster
2. 根据 cluster 找到相关的星系
3. 通过 `DocumentGalaxyLink` 找到星系下的所有文档
4. 返回传唤名单

核心方法：
```python
async def summon_witnesses(query: str, limit_per_galaxy: int = 3) -> List[Dict]
async def summon_single_galaxy(galaxy_id: str, limit: int = 5) -> List[Dict]
```

依赖：
- `ThesaurusManager`: 管理星系映射表
- `DocumentGalaxyLink`: 文档 - 星系关联表

---

### 2.3 取证器 (Collector) - v2.0 证据分片版
**文件**: `backend/app/services/intelligence/court/collector.py`

**架构变更**: 绕过单文档 Integrator，直接返回证据分片

职责：
1. 接收传唤文档列表
2. 为每个文档并行执行检索（Scout + PyramidHarvester + Examiner）
3. 返回证据分片（不调用 Integrator）

核心方法：
```python
async def collect_evidence(summoned_docs: List[Dict], query: str) -> List[Dict]
async def _collect_single_doc(doc: Dict, query: str) -> Dict
async def _scout(query: str) -> List[str]  # 查询拆解
async def _examiner(query: str, chunks: List[Dict], doc_id: str) -> List[Dict]  # 选择分片
async def _load_toc(doc_id: str) -> List[Dict]  # 加载 TOC
async def _load_chunks(selected_chunks: List[Dict]) -> List[Dict]  # 加载完整分片
```

关键流程：
1. **Scout**: 将查询拆解为 3 个子任务
2. **PyramidHarvester**: 针对每个子任务检索 10 个分片
3. **Examiner**: 基于 TOC 和指纹库选择 3-5 个核心分片
4. **Load**: 从数据库加载完整分片内容

兜底策略：
- Scout 失败：返回原查询
- Examiner 选择为空：使用 RRF 分数最高的前 3 个分片

---

### 2.4 大法官 (Moderator) - v2.0 证据分片裁决版
**文件**: `backend/app/services/intelligence/court/moderator.py`

**架构变更**: 基于证据分片检测冲突，而非证词

职责：
1. 在证据分片层面检测逻辑冲突
2. 对冲突进行裁决
3. 基于裁决结果生成最终判决书

核心方法：
```python
async def adjudicate(evidence_packages: List[Dict], query: str) -> Dict
async def _detect_conflicts(evidence_packages: List[Dict], query: str) -> List[Dict]
async def _resolve_conflict(conflict: Dict, query: str, evidence_packages: List[Dict]) -> Dict
async def _generate_verdict(evidence_packages: List[Dict], conflicts: List[Dict], query: str) -> Dict
```

冲突检测策略：
- 提取每个证据包的核心主张
- 使用 LLM 判断主张之间是否存在矛盾

裁决原则：
1. 优先采信证据更充分、逻辑更清晰的证词
2. 如果双方证据相当，采取兼容性解释
3. 如果有外部佐证（多个文档指向同一结论），优先采信

---

### 2.5 联邦法庭统一入口
**文件**: `backend/app/services/intelligence/court/federated_court.py`

职责：编排 Distributor、Collector、Moderator，完成多文档联邦检索

核心方法：
```python
async def hear(query: str, limit_per_galaxy: int = 3) -> Dict
async def hear_single(query: str, doc_id: str) -> Dict  # 单文档听证（备用）
```

执行流程：
```
阶段 1: 传唤证人 → summoned_docs
阶段 2: 收集证据 → evidence_packages
阶段 3: 裁决冲突 → verdict
休庭
```

返回结构：
```json
{
  "final_answer": "最终答案",
  "confidence": 0.0-1.0,
  "cited_galaxies": ["星系名 1", "星系名 2"],
  "reasoning": "推理过程",
  "conflicts_resolved": [...]
}
```

---

### 2.6 星系映射表管理器
**文件**: `backend/app/services/intelligence/court/thesaurus.py`

职责：管理 ThesaurusMap，支持聚类查询

核心方法：
```python
def find_clusters_by_query(query: str) -> List[str]  # 匹配 query 到 cluster
def get_all_galaxy_ids(cluster_ids: List[str]) -> Set[str]  # 获取星系 ID 集合
def get_galaxy_info(galaxy_id: str) -> Optional[Dict]  # 获取星系信息
```

数据来源：
- `backend/storage/thesaurus_map.json`: 由 `scripts/generate_thesaurus_map.py` 生成

---

## 3. 测试脚本

**文件**: `tests/debug_tools/test_federated_court.py`

测试场景：
- 查询："信息安全中的加密方法有哪些？"
- 验证：传唤证人列表、证据分片详情、冲突检测、最终判决书

测试输出示例：
```
📋 传唤证人列表
  1. Galaxy_密码学_理论 → 87d2d2c2... (5 个证据分片)
  2. Galaxy_Retrieval_Benchmarks → bcd1c05e... (3 个证据分片)
  3. Galaxy_评估_Synthetic → 09b552ba... (3 个证据分片)
  4. Galaxy_Algorithm → bbd90abf... (3 个证据分片)
  5. Galaxy_Gfm → f3350f17... (3 个证据分片)

✅ [Moderator] 裁决完成
【答案】信息安全中的加密方法主要分为对称加密和非对称加密...
【置信度】0.95
```

---

## 4. 关键架构决策

### 决策 1: 证据分片为裁决单位
**问题**: 多文档场景下，是否应该先合成证词再比较？  
**决策**: 否。直接在证据分片层面进行冲突分析和裁决。  
**理由**: 
- 避免 Integrator 的先验合成丢失细节
- Moderator 可以直接对比原始证据，更准确检测冲突
- 用户明确指示："多文档直接在得到证据分片前把证据分片分发给冲突分析节点分析冲突，让法官裁决"

### 决策 2: 保持星系写入确定性
**问题**: 是否需要动态合并星系？  
**决策**: 否。星系写入保持简单，合并逻辑放在异步代谢层。  
**理由**:
- 避免写入流复杂化
- 减少数据漂移风险
- ThesaurusMap 已提供逻辑层统一

### 决策 3: 并行取证
**问题**: 是否应该串行处理每个证人？  
**决策**: 否。使用 `asyncio.gather` 并行执行。  
**理由**:
- 证人文档之间相互独立
- 显著降低延迟（5 个文档并行 vs 串行）

---

## 5. 依赖关系图

```
FederatedCourt
├── Distributor
│   ├── ThesaurusManager
│   └── DocumentGalaxyLink (DB)
├── Collector
│   ├── Scout (LLM)
│   ├── PyramidHarvester
│   │   ├── PostgresStore (Vector DB)
│   │   └── KeywordExtractor
│   └── Examiner (LLM)
└── Moderator
    ├── Conflict Detection (LLM)
    ├── Conflict Resolution (LLM)
    └── Verdict Generation (LLM)
```

---

## 6. 文件清单

### 新建文件
| 文件 | 行数 | 描述 |
|------|------|------|
| `backend/app/services/intelligence/court/state.py` | ~60 | 状态契约定义 |
| `backend/app/services/intelligence/court/thesaurus.py` | ~80 | 星系映射表管理 |
| `backend/app/services/intelligence/court/distributor.py` | ~110 | 传唤官 |
| `backend/app/services/intelligence/court/collector.py` | ~240 | 取证器 |
| `backend/app/services/intelligence/court/moderator.py` | ~260 | 大法官 |
| `backend/app/services/intelligence/court/federated_court.py` | ~135 | 统一入口 |
| `tests/debug_tools/test_federated_court.py` | ~95 | 测试脚本 |

### 修改文件
| 文件 | 修改内容 |
|------|----------|
| `backend/app/services/keyword_extractor.py` | 导入路径修复 |
| `backend/app/services/intelligence/witness/nodes.py` | TOC 加载、RRF 兜底 |

---

## 7. 测试结果

**测试命令**: `python tests/debug_tools/test_federated_court.py`

**测试查询**: "信息安全中的加密方法有哪些？"

**结果摘要**:
- ✅ 传唤 5 个证人文档
- ✅ 收集 17 个证据分片（密码学文档 5 个，其他各 3 个）
- ✅ 检测到 0 个冲突
- ✅ 生成判决书，置信度 0.95
- ✅ 正确回答 DES、3DES、AES、SM4 等加密方法

---

## 8. 待实现功能

### P3: 联网证人系统
- `CitationExtractor`: 引用关系提取
- `Networker`: 增援证人传唤
- 测试：引用链检索

### P3: ChunkRevision 集成
- 将法庭裁决结论写入 `ChunkRevision` 表
- Git 备份记录

### P4: 性能优化
- 向量索引（如果查询延迟>5s）
- 缓存层（ThesaurusMap、证据分片）

---

## 9. 下一步行动

1. ✅ 联邦法庭核心功能完成
2. ⏳ 记录实现日志（当前）
3. ⏳ 实现联网证人系统（需要时）

---

**记录人**: Claude Code  
**验证状态**: ✅ 测试通过  
**最后更新**: 2026-04-15
