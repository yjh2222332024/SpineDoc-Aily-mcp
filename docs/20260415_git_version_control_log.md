# 📜 Git 版本管理实现日志 (2026-04-15)

**作者**: Karpathy (AI 顾问)  
**状态**: ✅ 核心功能完成，测试通过
**主题**: 极简 Git 版本管理设计

---

## 1. 核心洞察

### 洞察 1：Git 原生即溯源

> "Don't reinvent the version control wheel."

**问题**：传统 RAG 系统知识库更新后无历史、不可追溯。

**解决**：直接用 Git 原生能力，不额外设计 Revision 表。

| 需求 | Git 原生方案 |
|------|-------------|
| 版本溯源 | `git log chunks/{id}.json` |
| 查看历史版本 | `git show {commit}:chunks/{id}.json` |
| 回滚 | `git revert {commit}` |
| 分支管理 | `git branch/checkout` |

---

### 洞察 2：数据库与 Git 职责分离

```
数据库 (Chunk 表)         Git 仓库 (backend/storage/git-repo)
    ↓                           ↓
存储最新状态               存储历史快照
CRUD 操作直接更新           异步提交用于溯源
高效查询                    可回滚/可审计
```

**关键设计**：
- 数据库只存 `Chunk.content`（文本层）
- Git 存完整快照（含 metadata）
- CRUD 不阻塞，Git 提交异步

---

## 2. 架构设计

### 2.1 数据流

```
法庭裁决
    ↓
识别知识增量
    ↓
更新数据库 Chunk.content
    ↓
GitManager.commit_chunk() ← 异步/同步可选
    ↓
chunks/{id}.json 快照
    ↓
git commit -m "更新 Chunk xxx - 裁决原因"
```

### 2.2 提交消息规范

```
[evolution] 裁决 "{query[:30]}..." - {冲突数} 处冲突

- 冲突 1: [RED] 旧定义 vs 新定义
- 冲突 2: [YELLOW] 单一来源待验证
- 新增证据：[GREEN] arxiv.org

裁决结论：采用 2025 定义
```

---

## 3. 实现细节

### 3.1 GitManager 核心方法

```python
class GitManager:
    def commit_chunk(
        self,
        chunk_id: str,
        content: str,
        metadata: Dict,
        message: str
    ) -> Optional[str]:
        """
        提交 Chunk 快照
        
        1. 检查是否有变更（对比旧内容）
        2. 写入 chunks/{id}.json
        3. git add + commit
        4. 返回 commit_hash
        """

    def get_chunk_history(
        self,
        chunk_id: str,
        limit: int = 20
    ) -> List[GitCommit]:
        """获取 Chunk 的 Git 历史"""

    def get_chunk_at_commit(
        self,
        chunk_id: str,
        commit_hash: str
    ) -> Optional[Dict]:
        """获取指定提交时的 Chunk 内容"""

    def revert_chunk(
        self,
        chunk_id: str,
        commit_hash: str
    ) -> bool:
        """回滚 Chunk 到指定版本"""
```

### 3.2 无变更跳过优化

```python
# 检查是否有实际变更
old_data = json.load(open(filepath))
if old_data.get("content") == new_content:
    return None  # 跳过提交
```

**效果**：避免 Git 历史被重复内容污染。

---

## 4. 测试结果

### 4.1 原子化测试

| 测试项 | 预期 | 结果 |
|--------|------|------|
| 初始化仓库 | 创建 `.git` 目录 | ✅ |
| 提交 v1 | 返回 commit_hash | ✅ `d244f1ef` |
| 提交 v2 | 返回新 commit_hash | ✅ `af194140` |
| 无变更跳过 | 返回 `None` | ✅ |
| 查询历史 | 返回 2 条记录 | ✅ |
| 获取历史版本 | 返回 v1 内容 | ✅ "这是第一版内容" |
| 回滚 | 成功 + 内容恢复 | ✅ |

### 4.2 测试代码

```python
manager = GitManager()

# 提交 v1
hash1 = manager.commit_chunk(
    chunk_id='test-001',
    content='第一版内容',
    metadata={'page': 1},
    message='feat: 创建测试 Chunk v1'
)

# 提交 v2
hash2 = manager.commit_chunk(
    chunk_id='test-001',
    content='第二版内容',
    metadata={'page': 1},
    message='feat: 更新 Chunk v2'
)

# 查询历史
history = manager.get_chunk_history('test-001')
# → [hash2, hash1]

# 回滚
manager.revert_chunk('test-001', hash1)
```

---

## 5. 文件清单

| 文件 | 行数 | 描述 |
|------|------|------|
| `backend/app/services/knowledge/git_manager.py` | ~220 | GitManager 核心实现 |
| `backend/storage/git-repo/` | - | Git 仓库目录（运行时创建） |

---

## 6. CLI 命令规划

```bash
# 查看 Chunk 历史
spine history --chunk <chunk_id>

# 查看历史版本内容
spine show --chunk <chunk_id> --commit <hash>

# 回滚
spine revert --chunk <chunk_id> --to <hash>

# 查看提交详情
spine diff --commit <old_hash> --commit <new_hash>
```

---

## 7. 用户权限设计

### 模式 A：自动提交（可信用户）
```python
# 法庭裁决后直接提交
git_manager.commit_chunk(...)
```

### 模式 B：人工审核（访客模式）
```python
# 写入待审核队列
pending_revisions.add({...})

# 用户审核后手动提交
spine revisions approve <id>
```

---

## 8. 下一步行动

### P0: 集成到联邦法庭
- [ ] 在 `Moderator._generate_verdict` 中识别知识增量
- [ ] 调用 `GitManager.commit_chunk()` 提交变更
- [ ] 记录 `git_commit_hash` 到判决结果

### P1: CLI 命令实现
- [ ] `spine history` - 查看历史
- [ ] `spine show` - 查看版本
- [ ] `spine revert` - 回滚

### P2: Web UI（远期规划）
- [ ] 可视化历史时间线
- [ ] 一键回滚按钮
- [ ] 分支管理界面

---

## 9. 技术细节

### 9.1 为什么用 JSON 存储快照？

| 格式 | 优点 | 缺点 | 选择 |
|------|------|------|------|
| JSON | 结构化、可读、易解析 | 体积稍大 | ✅ 选择 |
| 纯文本 | 最小体积 | 无 metadata | ❌ |
| 二进制 | 最小体积 | 不可读 | ❌ |

### 9.2 Git 仓库位置约定

```
backend/
└── storage/
    └── git-repo/          ← Git 仓库根目录
        ├── .git/
        └── chunks/        ← Chunk 快照目录
            ├── abc123.json
            └── def456.json
```

---

**记录人**: Claude Code (Karpathy 模式)  
**最后更新**: 2026-04-15  
**测试状态**: ✅ 7/7 测试通过
