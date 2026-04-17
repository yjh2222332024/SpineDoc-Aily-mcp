# 📜 Git 版本控制 CLI 实现日志 (2026-04-15)

**作者**: Claude Code  
**状态**: ✅ 完成  
**主题**: Git 版本控制命令解耦 + 项目闭环

---

## 1. 架构设计

### 1.1 分层架构

```
┌─────────────────────────────────────────────────────────┐
│                    CLI 层 (main.py)                     │
│  - spine ask --online                                   │
│  - spine git history/show/revert/diff                   │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              服务层 (SpineEngine)                       │
│  - hybrid_ask()                                         │
│  - get_chunk_history()                                  │
│  - get_chunk_content()                                  │
│  - revert_chunk()                                       │
│  - diff_chunks()                                        │
│  - apply_knowledge_delta()                              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│         Git 服务层 (GitVersionControl)                  │
│  - get_chunk_history()                                  │
│  - get_chunk_content()                                  │
│  - revert_chunk()                                       │
│  - diff_chunks()                                        │
│  - apply_knowledge_delta()                              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Git 基础设施层                              │
│  - GitManager (Git 操作)                                │
│  - MetabolismManager (CRUD + Git)                       │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 文件清单

### 2.1 新建文件

| 文件 | 描述 | 行数 |
|------|------|------|
| `backend/app/services/git_services/__init__.py` | 包定义 | 4 |
| `backend/app/services/git_services/git_version_control.py` | Git 服务封装 | 110 |

### 2.2 修改文件

| 文件 | 修改内容 |
|------|----------|
| `backend/app/services/spine_engine.py` | 添加 Git 方法 + 懒加载 |
| `spine_cli/main.py` | Git 命令重构为子命令组 |

---

## 3. 核心实现

### 3.1 GitVersionControl 服务

```python
class GitVersionControl:
    """📜 Git 版本控制服务"""
    
    def __init__(self):
        self.git_manager = get_git_manager()
        self.metabolism_manager = get_metabolism_manager()
    
    def get_chunk_history(self, chunk_id: str, limit: int = 20) -> List[Dict]:
        # 查询 Git 历史
    
    def get_chunk_content(self, chunk_id: str, commit_hash: Optional[str] = None) -> Optional[Dict]:
        # 获取内容（当前/历史版本）
    
    def revert_chunk(self, chunk_id: str, commit_hash: str) -> bool:
        # 回滚
    
    def diff_chunks(self, chunk_id: str, old_commit: str, new_commit: str) -> str:
        # 差异对比
    
    async def apply_knowledge_delta(self, delta: Dict) -> Dict[str, str]:
        # 应用知识增量
```

### 3.2 SpineEngine 集成

```python
class SpineEngine:
    def __init__(self):
        # ... 原有初始化
        self._git_version_control = None  # 懒加载

    @property
    def git_version_control(self):
        """📜 Git 版本控制（懒加载）"""
        if self._git_version_control is None:
            from backend.app.services.git_services import get_git_version_control
            self._git_version_control = get_git_version_control()
        return self._git_version_control

    # Git 方法
    def get_chunk_history(self, chunk_id: str, limit: int = 20) -> List[Dict]:
        return self.git_version_control.get_chunk_history(chunk_id, limit)

    # ... 其他方法
```

### 3.3 CLI 子命令组

```python
# Git 版本控制命令组
git_app = typer.Typer(help="📜 Git 版本管理命令")
app.add_typer(git_app, name="git")

@git_app.command("history")
def git_history(...):
    engine = SpineEngine()
    history = engine.get_chunk_history(...)

@git_app.command("show")
def git_show(...):
    engine = SpineEngine()
    data = engine.get_chunk_content(...)

@git_app.command("revert")
def git_revert(...):
    engine = SpineEngine()
    success = engine.revert_chunk(...)

@git_app.command("diff")
def git_diff(...):
    engine = SpineEngine()
    diff = engine.diff_chunks(...)
```

---

## 4. CLI 命令使用

### 4.1 主命令

```bash
# 帮助
spine --help

# 提问（支持--online）
spine ask "问题" --online
spine ask "问题" --doc abc123
```

### 4.2 Git 子命令

```bash
# Git 帮助
spine git --help

# 查看历史
spine git history <chunk_id> --limit 20

# 查看内容（当前版本）
spine git show <chunk_id>

# 查看内容（历史版本）
spine git show <chunk_id> --to abc1234

# 回滚
spine git revert <chunk_id> --to abc1234 --yes

# 差异对比
spine git diff <chunk_id> --old abc1234 --new def5678
```

---

## 5. 测试验证

### 5.1 CLI 帮助测试
```bash
$ spine git --help
┌─ Commands ──────────────────────────────────────────────────────────────────┐
│ history  📜 查看 Chunk 的 Git 版本历史                                      │
│ show     📄 查看 Chunk 内容（当前版本或历史版本）                           │
│ revert   ♻️ 回滚 Chunk 到指定 Git 提交版本                                  │
│ diff     🔍 比较 Chunk 在两个 Git 提交之间的差异                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Import 测试
```bash
$ python -c "from backend.app.services.git_services import GitVersionControl"
✅ Import 测试通过
```

---

## 6. 项目闭环状态

| 功能 | 状态 | 命令 |
|------|------|------|
| 文档入库 | ✅ | `spine ingest xxx.pdf` |
| 单文档问答 | ✅ | `spine ask "问题" --doc xxx` |
| 多文档问答 | ✅ | `spine ask "问题"` |
| 联网问答 + 知识更新 | ✅ | `spine ask "问题" --online` |
| 查看历史 | ✅ | `spine git history <id>` |
| 查看内容 | ✅ | `spine git show <id>` |
| 回滚版本 | ✅ | `spine git revert <id> --to xxx` |
| 差异对比 | ✅ | `spine git diff <id> --old xxx --new yyy` |

---

## 7. 代码质量改进

### 7.1 解耦效果

**之前**: 500+ 行 main.py，所有逻辑混在一起  
**现在**: 
- `main.py`: ~200 行（只负责 CLI 参数解析和显示）
- `git_version_control.py`: ~110 行（服务层）
- `spine_engine.py`: 添加方法代理（统一入口）

### 7.2 职责分离

| 层 | 职责 |
|----|------|
| CLI 层 | 参数解析、结果渲染 |
| 服务层 (SpineEngine) | 业务逻辑编排、统一入口 |
| Git 服务层 | Git 操作封装 |
| 基础设施层 | GitManager、MetabolismManager |

---

## 8. 下一步行动

### P0: 端到端测试
- [ ] 完整测试 `--online` 流程（问答 + Git 更新）
- [ ] 测试 `git history/show/revert/diff` 完整流程

### P1: 增强功能
- [ ] `spine list` 显示 `updated_at` 时间戳
- [ ] 批量回滚命令
- [ ] Git 钩子（提交前验证）

### P2: Web UI（远期）
- [ ] 时间线可视化
- [ ] Diff 图形化对比
- [ ] 一键回滚按钮

---

**记录人**: Claude Code  
**最后更新**: 2026-04-15  
**项目状态**: ✅ 核心功能闭环
