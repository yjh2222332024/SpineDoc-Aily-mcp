# 🌐 联网模式实现日志 (2026-04-15)

**作者**: Claude Code  
**状态**: ✅ 完成  
**主题**: `--online` 参数集成 + 知识库动态更新流程

---

## 1. 架构设计

### 1.1 路由逻辑

```
spine ask
    │
    ├─ --doc xxx + NOT --online  →  _single_doc_witness()  (witness_graph)
    └─ 其他情况                  →  _federated_court()     (FederatedCourt)
                                       │
                                       └─ enable_online=True → 互联网证人 + Git 更新
```

### 1.2 模式对比

| 模式 | 命令 | 流程 | 知识更新 |
|------|------|------|----------|
| 单文档深度质证 | `--doc xxx` | `witness_graph` 状态机 | ❌ |
| 本地联邦法庭 | (无参数) | `FederatedCourt.hear()` | ❌ |
| 联网联邦法庭 | `--online` | `FederatedCourt.hear(enable_online=True)` | ✅ Git 提交 |
| 联网单文档 | `--online --doc xxx` | `FederatedCourt.hear(enable_online=True)` | ✅ Git 提交 |

> **关键设计决策**: 即使 `--online --doc xxx` 指定了单文档，仍然走联邦法庭流程，因为互联网证人引入了至少一个额外证据源，构成"多文档"场景。

---

## 2. 文件修改清单

### 2.1 `backend/app/services/spine_engine.py`

**修改内容**:
1. 添加 `enable_online: bool = False` 参数到 `hybrid_ask()`
2. 添加路由逻辑
3. 新增 `_single_doc_witness()` 方法（原 `hybrid_ask` 逻辑）
4. 新增 `_federated_court()` 方法（调用 `FederatedCourt.hear()`）

**代码片段**:
```python
async def hybrid_ask(
    self,
    query: str,
    doc_id: str = "all",
    limit: int = 15,
    api_key: Optional[str] = None,
    enable_online: bool = False
) -> List[Dict[str, Any]]:
    if doc_id != "all" and not enable_online:
        return await self._single_doc_witness(query, doc_id)
    else:
        return await self._federated_court(query, doc_id, enable_online)
```

### 2.2 `spine_cli/main.py`

**修改内容**:
1. 添加 `--online/-o` 参数到 `ask` 命令
2. 显示判决元数据（置信度、引用星系、知识增量）
3. 调用 `MetabolismManager.apply()` 处理 Git 提交

**代码片段**:
```python
@app.command()
def ask(
    query: str = typer.Argument(..., help="你的问题"),
    doc: str = typer.Option("all", "--doc", "-d", help="目标文档 ID"),
    limit: int = typer.Option(15, "--limit", "-l", help="召回上限"),
    api_key: Optional[str] = typer.Option(None, "--key", "-k", help="注入私有 API Key"),
    online: bool = typer.Option(False, "--online", "-o", help="🌐 激活联网证人并触发知识库更新")
):
    # ...
    if online and verdict_meta.get("knowledge_delta", {}).get("has_delta"):
        metabolism = get_metabolism_manager()
        commit_results = await metabolism.apply(delta)
```

### 2.3 `backend/app/services/intelligence/court/federated_court.py`

**修复内容**:
- 添加 `state = CourtState()` 初始化（之前遗漏导致 NameError）

---

## 3. 数据流

```
用户执行 spine ask --online "问题"
         │
         ▼
┌─────────────────────┐
│  spine_cli/main.py  │
│  - 解析--online 参数   │
│  - 调用 hybrid_ask   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  SpineEngine        │
│  hybrid_ask()       │
│  - 路由到           │
│    _federated_court │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  FederatedCourt     │
│  hear()             │
│  - Distributor      │
│  - Collector        │
│  - Moderator        │
│    - 识别 delta     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  CLI 层 (main.py)   │
│  - 检查 knowledge_  │
│    delta            │
│  - 调用             │
│    MetabolismMgr    │
│  - Git 提交          │
└─────────────────────┘
```

---

## 4. 测试验证

### 4.1 Import 测试
```bash
$ python -c "from backend.app.services.spine_engine import SpineEngine"
✅ Import 测试通过
```

### 4.2 CLI 帮助测试
```bash
$ python spine_cli/main.py ask --help
 Usage: main.py ask [OPTIONS] QUERY

┌─ Options ───────────────────────────────────────────────────────────────────┐
│ --online  -o               🌐 激活联网证人并触发知识库更新                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. 下一步行动

### P0: 端到端测试
- [ ] 使用真实文档测试 `--online` 流程
- [ ] 验证 Git 提交记录
- [ ] 验证颜色置信度显示

### P1: CLI 增强
- [ ] `spine history --chunk <id>` 查看 Chunk 历史
- [ ] `spine revert --to <commit>` 回滚功能
- [ ] `spine revisions` 管理待审核更新

### P2: 配置优化
- [ ] 将互联网证人 API key 移到配置
- [ ] 添加 `AUTO_COMMIT` 配置项（审核模式）

---

## 6. 技术细节

### 6.1 为什么 `--online --doc xxx` 不走单文档流程？

**原因**: 互联网证人引入至少一个额外证据源，构成多文档场景。单文档 `witness_graph` 流程假设只有一个文档，不适用。

**解决方案**: 统一走联邦法庭流程，由 Moderator 裁决冲突。

### 6.2 为什么 Git 提交在 CLI 层不在 Engine 层？

**原因**: 职责分离
- `SpineEngine`: 只负责路由/调度
- `FederatedCourt`: 只负责裁决
- `MetabolismManager`: 只负责 Git 事务
- CLI 层: 决定何时提交（可配置为审核模式）

**好处**: 
- 未来可添加 `--no-commit` 参数
- 可改为写入待审核队列
- 测试时不污染 Git

---

**记录人**: Claude Code  
**最后更新**: 2026-04-15  
**测试状态**: ✅ Import 测试通过，CLI 参数已显示
