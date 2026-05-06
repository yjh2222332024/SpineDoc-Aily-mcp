# 🕸️ SpineDoc V7.0 逻辑织网协议

**创建日期**: 2026-04-16  
**状态**: 已实现  
**作者**: SpineDoc Team

---

## 📜 核心哲学

> "关联不是数据录入，是审判后的质证结论。"

在 SpineDoc 的知识系统中，**关系是昂贵的**，不是廉价的联想。

每一条连接键都代表系统对事实关联的**郑重承诺**，必须经过联邦法庭的审判才能生成。

---

## 🎯 设计目标

### 问题：A-MEM 的状态爆炸

A-MEM (NeurIPS 2025) 的问题：
- 每次检索自动发现连接 → O(N²) 爆炸
- 关系是"联想产物"，没有约束
- 无法追溯关系的来源

### SpineDoc 的解决方案

**严格模式**：
```
联邦法庭审判 → Moderator 裁决 → GraphWeaver 缝合 → Git 版本控制
```

关系的增删改查**全部同步到 Git**，与 Chunk 进化一致。

---

## 🏗️ 架构设计

### 数据模型

```python
class RelationshipType(str, Enum):
    """关系谓词枚举（严格，不可私造）"""
    CAUSALITY = "causality"        # A 导致 B
    CONTRADICTION = "contradiction" # A 与 B 矛盾
    SUPPORT = "support"            # A 支撑 B
    EVOLUTION = "evolution"        # B 是 A 的修正版
    COMPLEMENT = "complement"      # A 和 B 互补


class ChunkRelationship(SQLModel, table=True):
    """关系表"""
    id: UUID
    source_chunk_id: UUID  # 外键
    target_chunk_id: UUID  # 外键
    rel_type: RelationshipType
    strength: float  # 0.0-1.0
    description: str
    verdict_id: UUID  # 触发关系的审判 ID
    created_at: datetime
```

### 核心组件

```
┌─────────────────────────────────────────────────────────────┐
│                    V7.0 逻辑织网架构                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FederatedCourt                                             │
│    │                                                        │
│    ├─► Distributor (传唤证人)                               │
│    ├─► Collector (收集证据)                                 │
│    └─► Moderator (大法官裁决)                               │
│           │                                                 │
│           │ Verdict {                                       │
│           │   proposed_relationships: [...]                 │
│           │ }                                               │
│           ▼                                                 │
│    GraphWeaver (缝合者)                                     │
│           │                                                 │
│           ├─► 验证关系声明                                  │
│           ├─► 物理化到数据库                                │
│           └─► 同步提交 Git                                  │
│                                                             │
│    Git Repository                                           │
│           ├── chunks/         # Chunk 快照                  │
│           └── relationships/  # 关系快照 🕸️ [V7.0]          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 实现细节

### GraphWeaver 严格验证

```python
def _create_relationship(...) -> ChunkRelationship:
    # === 严格验证阶段 ===

    # 1. 验证关系类型（必须是枚举值）
    try:
        relationship_type = RelationshipType(rel_type)
    except ValueError:
        raise GraphWeaverError(f"无效的关系类型 '{rel_type}'")

    # 2. 验证强度范围
    assert 0.0 <= strength <= 1.0

    # 3. 禁止自环
    assert source_chunk_id != target_chunk_id

    # 4. 验证 Chunk 存在性
    self._validate_chunk_exists(source_chunk_id)
    self._validate_chunk_exists(target_chunk_id)

    # === 物理化阶段 ===
    # 1. 数据库记录
    # 2. Git 提交（同步）
```

### Git 版本控制

关系文件的目录结构：
```
backend/storage/git-repo/
├── chunks/
│   ├── {chunk_id}.json
│   └── ...
└── relationships/  🕸️ [V7.0 新增]
    ├── {rel_id}.json
    └── ...
```

关系文件内容：
```json
{
  "id": "rel-uuid",
  "source_chunk_id": "chunk-a-uuid",
  "target_chunk_id": "chunk-b-uuid",
  "rel_type": "contradiction",
  "strength": 0.95,
  "description": "两个 Chunk 在密钥长度描述上存在直接矛盾",
  "verdict_id": "verdict-uuid",
  "created_at": "2026-04-16T20:00:00Z",
  "updated_at": "2026-04-16T20:00:00Z"
}
```

Git 提交消息格式：
```
[create] contradiction: chunk-a -> chunk-b
[update] 关系 rel-uuid: strength 0.8 -> 0.95
[delete] 删除关系 rel-uuid: chunk-a -[contradiction]-> chunk-b
```

---

## 📊 使用场景

### 场景 1：冲突检测生成关系

```python
# 联邦法庭审判后
verdict = await court.hear(query="SM4 的密钥长度")

# Verdict 结构
{
  "proposed_relationships": [
    {
      "source_chunk_id": "6021e448-...",
      "target_chunk_id": "7a3f9b21-...",
      "rel_type": "contradiction",
      "strength": 0.95,
      "description": "两个 Chunk 在密钥长度描述上存在直接矛盾"
    }
  ]
}

# GraphWeaver 自动缝合 + Git 提交
```

### 场景 2：关系历史追溯

```bash
# 查看关系的 Git 历史
spine git relationship-history rel-uuid

# 输出示例
$ git log relationships/rel-uuid.json
commit abc123
Author: GraphWeaver
Date:   2026-04-16T20:00:00Z

    [update] 关系 rel-uuid: strength 0.8 -> 0.95
```

### 场景 3：关系网络可视化

```python
# 获取指定 Chunk 的关系网络
network = weaver.get_relationship_network(chunk_id, max_depth=2)

# 输出
{
  "nodes": ["chunk-a", "chunk-b", "chunk-c"],
  "edges": [
    {"source": "chunk-a", "target": "chunk-b", "type": "contradiction"},
    {"source": "chunk-a", "target": "chunk-c", "type": "support"}
  ]
}
```

---

## 🧪 测试

运行测试：
```bash
.venv/Scripts/python.exe tests/test_graph_weaver.py
```

测试场景：
1. 模拟 Verdict 包含 proposed_relationships
2. 调用 GraphWeaver.weave_from_verdict()
3. 验证数据库记录 + Git 提交

---

## 📝 实施路线图

| 阶段 | 任务 | 状态 |
|------|------|------|
| P0 | Schema 部署 | ✅ 完成 |
| P0 | 谓词标准化 | ✅ 完成 |
| P1 | Moderator 升级 | ✅ 完成 |
| P2 | GraphWeaver 实现 | ✅ 完成 |
| P2 | Git 同步集成 | ✅ 完成 |
| P3 | 可视化（可选） | 待开发 |

---

## 🏛️ 架构师训诫

> "平庸的系统在数据堆里挖洞，卓越的系统在逻辑之间架桥。"

我们给 Chunk 加上连接键，不是为了让数据库变得复杂，而是为了让知识不再是孤岛。

**记住**：每一条连接都是一份责任，代表了系统对事实关联的郑重承诺。

---

## 🔗 相关文件

- `backend/app/services/knowledge/graph_weaver.py` - 缝合者实现
- `backend/app/services/knowledge/git_manager.py` - Git 版本控制
- `backend/app/services/intelligence/court/moderator.py` - 大法官升级
- `backend/app/services/intelligence/court/federated_court.py` - 法庭集成
- `tests/test_graph_weaver.py` - 测试脚本

---

**最后更新**: 2026-04-16
