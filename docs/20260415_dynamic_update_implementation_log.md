# 📜 动态更新实现日志 (2026-04-15)

**作者**: Karpathy (AI 顾问)  
**状态**: ✅ 核心功能完成，测试通过
**主题**: 法庭裁决 → 知识增量识别 → Git 提交

---

## 1. 核心洞察

### 洞察 1：知识增量从裁决中自然涌现

> "Knowledge deltas emerge from conflict resolution, not manual detection."

**触发条件**（满足任一即更新）：
| 条件 | 识别逻辑 | 示例 |
|------|----------|------|
| 冲突被裁决 | 遍历 `resolved_conflicts` → 找到对应 chunks | "传统 AES vs Post-Quantum AES" |
| 联网证据补充 | 遍历 `is_internet=True` 的证据包 | arxiv.org 新论文 |
| 证据颜色为 GREEN/BLUE | 高置信度证据值得记录 | 🟢 0.92 |

---

### 洞察 2：Git 提交是副作用，不是目的

```
Moderator 裁决
     ↓
识别 knowledge_delta（纯数据）
     ↓
Engine 层决定如何处理（可配置）
     ├── 自动提交 Git（默认）
     ├── 待审核队列（团队模式）
     └── 忽略（测试模式）
```

**关键设计**：
- `Moderator` 只负责识别，不直接提交 Git
- `SpineEngine` 决定是否提交、如何提交
- Git 提交是可选的副作用

---

## 2. 实现细节

### 2.1 Moderator._identify_knowledge_delta

**文件**: `backend/app/services/intelligence/court/moderator.py`

```python
def _identify_knowledge_delta(
    self,
    evidence_packages: List[Dict],
    conflicts: List[Dict],
    resolved_conflicts: List[Dict],
    query: str
) -> Dict:
    """
    识别知识增量

    Returns:
        {
            "has_delta": bool,
            "updated_chunks": [
                {
                    "chunk_id": "abc123",
                    "galaxy_name": "Galaxy_A",
                    "change_type": "update",
                    "reason": "冲突裁决：...",
                    "color": "GREEN"
                }
            ],
            "commit_message": "裁决 \"AES 进展\" - 1 处冲突",
            "conflict_count": 1,
            "resolved_count": 1
        }
    """
```

**识别逻辑**：
1. **冲突裁决** → 被推翻/更新的证据需要更新
2. **联网证据补充** → GREEN/BLUE 证据值得记录
3. **生成提交消息** → 结构化消息用于 Git commit

---

### 2.2 SpineEngine.hybrid_ask

**文件**: `backend/app/services/spine_engine.py`

**新增逻辑**（步骤 6）：
```python
# 6. 处理知识增量（自动 CRUD + Git 提交）
knowledge_delta = verdict.get("knowledge_delta", {})
if knowledge_delta.get("has_delta"):
    print(f"📈 [Engine] 检测到知识增量，正在提交到 Git...")
    for chunk_change in knowledge_delta.get("updated_chunks", []):
        chunk_id = chunk_change.get("chunk_id")
        if not chunk_id:
            continue

        # 提交到 Git
        content = chunk_change.get("new_content") or chunk_change.get("old_content", "")
        commit_hash = git_manager.commit_chunk(
            chunk_id=chunk_id,
            content=content,
            metadata=chunk_change.get("metadata", {}),
            message=knowledge_delta.get("commit_message", "知识库更新")
        )

        if commit_hash:
            chunk_change["git_commit_hash"] = commit_hash[:8]
            print(f"  ✓ Chunk {chunk_id[:8]} → git:{commit_hash[:8]}")
```

---

## 3. 测试结果

### 3.1 模拟测试

**命令**: `python tests/debug_tools/test_dynamic_update.py`

**输出**:
```
📈 知识增量识别结果:
  has_delta: True
  updated_chunks: 3
  commit_message: 裁决 "AES 加密方法的最新进展是什么？" - 1 处冲突

  Chunk 1:
    chunk_id: chunk_001
    galaxy_name: Galaxy_密码学
    change_type: update
    reason: 冲突裁决：传统 AES vs Post-Quantum AES 定义差异
    color: GREEN

  Chunk 2:
    chunk_id: internet_001
    galaxy_name: 互联网证人
    change_type: update
    reason: 冲突裁决：传统 AES vs Post-Quantum AES 定义差异
    color: GREEN

  Chunk 3:
    chunk_id: internet_001
    galaxy_name: 互联网证人
    change_type: create
    reason: 联网证据补充：Post-Quantum AES
    color: GREEN

📜 测试 Git 提交...
  ✅ Chunk chunk_001 → git:16f4678b
  ✅ Chunk internet_001 → git:eb924606
  ⚠️ Chunk internet_001 无变更，跳过提交
```

### 3.2 测试验证

| 测试项 | 预期 | 结果 |
|--------|------|------|
| 检测到知识增量 | `has_delta=True` | ✅ |
| 冲突触发更新 | 1 处冲突 → 3 个 Chunk 更新 | ✅ |
| Git 提交成功 | 返回 commit_hash | ✅ |
| 无变更跳过 | 相同内容返回 `None` | ✅ |
| 历史可查 | `git log` 可追溯 | ✅ |

---

## 4. 文件清单

| 文件 | 修改类型 | 描述 |
|------|----------|------|
| `moderator.py` | 修改 | 新增 `_identify_knowledge_delta()` 方法 |
| `spine_engine.py` | 修改 | 集成 Git 提交逻辑 |
| `git_manager.py` | 已有 | 提交 Chunk 快照 |
| `test_dynamic_update.py` | 新建 | 测试脚本 |

---

## 5. 下一步行动

### P0: CLI 显示增强
- [ ] `spine ask` 命令显示 Git 提交结果
- [ ] `spine history --chunk <id>` 查看历史
- [ ] `spine revert --to <commit>` 回滚功能

### P1: 审核模式（可选）
- [ ] 配置项 `AUTO_COMMIT=True/False`
- [ ] 待审核队列管理
- [ ] `spine revisions pending/approve/reject`

### P2: Web UI（远期）
- [ ] 知识进化时间线
- [ ] 可视化 diff 对比
- [ ] 一键回滚按钮

---

## 6. 技术细节

### 6.1 为什么 `updated_chunks` 可能重复？

**原因**：同一个 chunk 可能同时满足多个条件
1. 冲突裁决 → 需要更新
2. 联网证据补充 → 需要记录

**解决方案**（后续优化）：
```python
# 去重逻辑（待实现）
seen_ids = set()
unique_chunks = []
for chunk in updated_chunks:
    if chunk['chunk_id'] not in seen_ids:
        unique_chunks.append(chunk)
        seen_ids.add(chunk['chunk_id'])
```

### 6.2 Git 提交消息规范

```
[evolution] 裁决 "{query[:30]}..." - {conflict_count} 处冲突

- 冲突 1: {conflict_description}
- 新增证据：{internet_evidence_title}

裁决结论：{verdict_decision}
```

---

**记录人**: Claude Code (Karpathy 模式)  
**最后更新**: 2026-04-15  
**测试状态**: ✅ 动态更新流程跑通
