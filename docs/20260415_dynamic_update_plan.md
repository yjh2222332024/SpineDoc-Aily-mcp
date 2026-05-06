# 📜 知识库动态更新实现规划 (2026-04-15)

**作者**: Karpathy (AI 顾问)  
**状态**: 📋 规划阶段
**主题**: 法庭裁决 → 自动 CRUD → Git 提交

---

## 1. 核心洞察

### 洞察 1：不是所有裁决都需要更新知识库

> "Only persist knowledge deltas, not queries."

**触发条件**（满足任一即更新）：
| 场景 | 是否触发 | 理由 |
|------|----------|------|
| 无冲突，本地证据充足 | ❌ 否 | 无知识增量 |
| 检测到冲突，Moderator 裁决 | ✅ 是 | 知识进化点 |
| 联网证据推翻本地证据 | ✅ 是 | 知识更新 |
| 多源印证新发现 | ✅ 是 | 知识补充 |

---

### 洞察 2：CRUD 操作自动化

**传统流程**（手动）：
```
用户发现问题 → 手动编辑文档 → 手动保存 → 手动 Git 提交
```

**自动化流程**：
```
法庭裁决 → 识别变更 → 自动更新 DB → 自动 Git 提交 → 返回 commit_hash
```

---

## 2. 架构设计

### 2.1 数据流

```
┌─────────────────────────────────────────────────────────────┐
│                     联邦法庭裁决                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        ↓                                       ↓
【有知识增量】                            【无知识增量】
        ↓                                       ↓
  识别变更 Chunk                           跳过更新
        ↓
  更新数据库 (Chunk.content)
        ↓
  GitManager.commit_chunk()
        ↓
  返回 git_commit_hash 到判决书
```

### 2.2 变更识别逻辑

```python
# Moderator 裁决后
def identify_knowledge_delta(verdict, evidence_packages):
    """
    识别知识增量
    
    Returns:
        {
            "has_delta": bool,
            "updated_chunks": [
                {
                    "chunk_id": "abc123",
                    "old_content": "旧内容",
                    "new_content": "新内容 (基于裁决)",
                    "change_type": "update/create/delete",
                    "reason": "2025 论文推翻旧定义"
                }
            ],
            "git_commit_message": "裁决 'RAG 进展' - 更新 2 处冲突"
        }
    """
```

---

## 3. 实现步骤

### Step 1: Moderator 输出增强

**修改文件**: `backend/app/services/intelligence/court/moderator.py`

**新增字段**:
```python
verdict = {
    "final_answer": "...",
    "confidence": 0.95,
    "cited_galaxies": ["Galaxy_A", "Galaxy_B"],
    "cited_chunks": [{"id": "abc123", "color": "GREEN", ...}],
    
    # ← 新增
    "knowledge_delta": {
        "has_delta": True,
        "updated_chunks": [
            {
                "chunk_id": "abc123",
                "change_type": "update",
                "old_content": "...",
                "new_content": "...",
                "reason": "联网证据推翻本地证据"
            }
        ],
        "commit_message": "裁决 \"RAG 进展\" - 更新 2 处冲突"
    }
}
```

---

### Step 2: SpineEngine 集成 CRUD + Git

**修改文件**: `backend/app/services/spine_engine.py`

**新增方法**:
```python
class SpineEngine:
    async def hybrid_ask(self, query, doc_id, limit):
        # ... 原有法庭逻辑
        
        # 裁决后处理知识增量
        verdict = await self.moderator.adjudicate(...)
        
        if verdict.get('knowledge_delta', {}).get('has_delta'):
            # 更新数据库 + Git 提交
            await self._apply_knowledge_delta(
                verdict['knowledge_delta']
            )
        
        return [verdict, ...]
    
    async def _apply_knowledge_delta(self, delta):
        """应用知识增量到数据库和 Git"""
        for chunk_change in delta['updated_chunks']:
            # 1. 更新数据库
            await self._update_chunk_db(chunk_change)
            
            # 2. 提交 Git
            commit_hash = self.git_manager.commit_chunk(
                chunk_id=chunk_change['chunk_id'],
                content=chunk_change['new_content'],
                metadata=chunk_change.get('metadata'),
                message=delta['commit_message']
            )
            
            # 3. 记录 commit_hash 到判决
            chunk_change['git_commit_hash'] = commit_hash
```

---

### Step 3: CLI 显示增强

**修改文件**: `spine_cli/main.py`

**ask 命令输出增强**:
```
🏛️ SpineDoc 联邦知识判决书
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RAG（检索增强生成）的最新进展包括：

1. 2025 年提出的 Sparse RAG 架构 (Galaxy_A) 🟢
2. 对比学习改进检索质量 (Galaxy_B) 🔵

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 逻辑溯源证据链
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
颜色       来源           页码   事实描述
🟢 0.87   第 3 章 RAG      P75   RAG 结合检索与生成...
🟡 0.42   互联网证人      P0    2025 最新进展...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📜 知识库更新
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 已更新 2 个 Chunk
   • Chunk abc123: git commit d244f1ef (更新原因：2025 论文推翻旧定义)
   • Chunk def456: git commit af194140 (更新原因：多源印证补充)
```

---

## 4. 关键设计决策

### 决策 1：何时触发更新？

**方案 A**: 每次裁决都更新（过于频繁）
**方案 B**: 仅冲突裁决更新（可能遗漏）
**方案 C**: 有"知识增量"时更新（✅ 选择）

**知识增量定义**:
1. 发现并裁决了冲突
2. 新增证据补充了现有知识
3. 时间敏感信息更新（如"最新进展"）

---

### 决策 2：用户权限控制

**自动提交模式**（默认）：
```python
git_manager.commit_chunk(...)  # 直接提交
```

**审核模式**（可配置）：
```python
if user in AUTO_COMMIT_USERS:
    git_manager.commit_chunk(...)
else:
    pending_revisions.add(...)  # 待审核队列
```

---

### 决策 3：Git 提交粒度

**方案 A**: 每个 Chunk 独立提交（历史清晰，但提交过多）
**方案 B**: 一次裁决合并提交（✅ 选择）

```python
# 一次裁决的所有变更合并为一个提交
commit_hash = git_manager.commit(
    message="裁决 \"RAG 进展\" - 更新 2 处冲突",
    files=["chunks/abc123.json", "chunks/def456.json"],
    operation="evolution"
)
```

---

## 5. 测试计划

### 5.1 单元测试
```python
def test_knowledge_delta_detection():
    # 无冲突 → 无增量
    assert identify_delta(no_conflict_verdict) == {"has_delta": False}
    
    # 有冲突 → 有增量
    assert identify_delta(conflict_verdict) == {"has_delta": True, ...}
```

### 5.2 集成测试
```python
async def test_end_to_end_update():
    # 1. 查询触发冲突
    verdict = await engine.hybrid_ask("RAG 最新进展")
    
    # 2. 验证 Git 提交
    assert verdict['knowledge_delta']['git_commit_hash'] is not None
    
    # 3. 验证历史可查
    history = git_manager.get_chunk_history('abc123')
    assert len(history) >= 1
```

---

## 6. 文件清单

| 文件 | 修改类型 | 描述 |
|------|----------|------|
| `moderator.py` | 修改 | 输出 knowledge_delta |
| `spine_engine.py` | 修改 | 集成 CRUD + Git |
| `git_manager.py` | 已有 | 提交快照 |
| `spine_cli/main.py` | 修改 | 显示更新结果 |

---

## 7. 下一步行动

1. ⏳ 修改 `moderator.py` - 输出 knowledge_delta
2. ⏳ 修改 `spine_engine.py` - 集成 CRUD + Git
3. ⏳ 修改 `spine_cli/main.py` - 显示更新结果
4. ⏳ 测试完整流程

---

**记录人**: Claude Code (Karpathy 模式)  
**最后更新**: 2026-04-15
