# 📜 架构演进规划日志 (2026-04-15)

**参与者**: Karpathy (AI 顾问), Uncle Bob (架构顾问), 用户  
**主题**: Git 版本管理 + 四色置信度 + CLI → Web 迁移规划

---

## 1. 核心洞察 (Karpathy)

### 洞察 1：查询持久化策略

> "Don't store queries, store **knowledge deltas**."

**决策**：只持久化"知识进化事件"

| 场景 | 是否持久化 | 理由 |
|------|------------|------|
| 无冲突，本地证据充足 | ❌ 否 | 无知识增量 |
| 检测到冲突，Moderator 裁决 | ✅ 是 | 知识进化点 |
| 互联网证人提供新证据 | ✅ 是 | 知识增量 |
| 时间敏感信息更新 | ✅ 是 | 知识迭代 |

---

### 洞察 2：Git 不是备份，是知识版本机

**核心设计**：

```
法庭裁决
   ↓
ChunkRevision (数据库)
   ↓
Git Commit (自动提交)
   ↓
知识库演进历史可追溯
```

**Commit 规范**：
```
feat(evolution): 裁决 "RAG 最新进展" - 发现 3 处冲突

- 冲突 1: [RED] 2024 vs 2025 RAG 定义差异
- 冲突 2: [YELLOW] 单一来源待验证
- 新增证据：[GREEN] 3 篇权威论文 (arxiv.org)

裁决结论：采用 2025 定义，标记旧证据为 deprecated
```

---

## 2. 四色置信度系统

### 颜色定义

| 颜色 | 名称 | 触发条件 | 用户感知 |
|------|------|----------|----------|
| 🟢 **GREEN** | AUTHORITATIVE | 权威来源 + 时间新鲜 + 多源印证 (≥2) | "权威，可引用" |
| 🔵 **BLUE** | VERIFIED | 多源一致，交叉印证 | "已验证，可信" |
| 🟡 **YELLOW** | UNVERIFIED | 单一来源，待验证 | "孤证，需注意" |
| 🔴 **RED** | CONFLICT | 检测到冲突，Moderator 已裁决 | "有争议，需人工介入" |

### 判定算法

```python
def _determine_color(score: float, source_count: int) -> ConfidenceColor:
    if has_conflict:
        return RED
    
    if source_count >= 2:
        # 多源印证
        if score > 0.8: return GREEN
        elif score > 0.6: return BLUE
        else: return YELLOW
    else:
        # 单一来源
        return YELLOW  # 高分但单源，仍是 YELLOW
```

### 用户界面渲染

**CLI 模式**：
```
📌 Chunk #1 | P75
🟢 AUTHORITATIVE (0.92)
📍 路径：第 3 章 分组密码 -> 3.2 AES
📄 内容：AES 被视为对称加密的黄金标准...
```

**Web 模式** (规划)：
```
[🟢 权威]  (鼠标悬停显示来源详情)
├─ 来源：arxiv.org, wikipedia.org (2 个独立来源)
├─ 时间：2025-03-01 (新鲜度 95%)
└─ 置信度：0.92
```

---

## 3. CLI → Web 迁移规划

### 当前 CLI 命令映射

| CLI 命令 | FastAPI 路由 | Web 页面 |
|----------|-------------|----------|
| `ingest` | `POST /documents` | 文档上传页 |
| `ask` | `POST /query` | 查询页 |
| `tree` | `GET /documents/{id}/toc` | 文档详情页 |
| `list` | `GET /documents` | 文档列表页 |
| `chunks` | `GET /documents/{id}/chunks` | 切片浏览器 |
| *(新增)* | `GET /evolution/history` | 知识进化史 |

### 目标架构

```
backend/app/
├── api/                    # ← 新建：FastAPI 路由层
│   ├── routes/
│   │   ├── documents.py    # ingest, tree, list, chunks
│   │   ├── query.py        # ask (联邦法庭)
│   │   ├── galaxies.py     # 星系管理
│   │   └── revisions.py    # ← 新建：知识进化历史
│   └── middleware/
├── services/
│   ├── spine_engine.py     # 已有：核心引擎
│   ├── intelligence/
│   │   └── court/          # 已有：联邦法庭 + 四色置信度
│   └── knowledge/          # ← 新建：Git 版本管理
│       ├── git_manager.py
│       └── evolution.py
├── core/
│   ├── config.py
│   └── models.py
└── db/                     # ← 新建：数据库会话管理
```

---

## 4. 实现步骤

### Phase 1: 四色置信度 + Git 版本管理
- [ ] `color_confidence.py` - 四色判定器
- [ ] `git_manager.py` - Git 提交管理器
- [ ] `evolution.py` - 进化触发器
- [ ] 修改 `Moderator` 输出增加 `color` 字段

### Phase 2: CLI 核心逻辑迁移到 Backend
- [ ] `spine_cli/main.py` → `backend/app/api/routes/`
- [ ] CLI 作为 API 的客户端存在
- [ ] 保证 API 可独立运行

### Phase 3: FastAPI + Web 前端
- [ ] FastAPI 路由层
- [ ] Web 页面 (React/Vue?)
- [ ] 用户版本管理界面

---

## 5. Git 提交粒度决策

**决策**：**每次冲突提交** + **用户手动触发批量提交**

### 自动提交（系统触发）
```python
# 在 Moderator 裁决后
if should_evolve(verdict):
    git_manager.commit(
        message=f"裁决：{query[:50]} - 发现 {len(conflicts)} 处冲突",
        changes=revision_data
    )
```

### 手动提交（用户触发）
```bash
# CLI 命令 (规划)
spine evolve commit -m "批量提交本周知识进化"

# Web 界面 (规划)
[提交到 Git] [创建分支] [回滚版本]
```

---

## 6. 用户版本管理功能

### 溯源查询
```bash
# CLI (规划)
spine history --chunk <chunk_id>
# 输出：
# Chunk abc123 演变历史:
# - 2026-04-15 10:00: 创建 (初始入库)
# - 2026-04-15 14:30: 裁决 "RAG 最新进展" - 标记为 YELLOW (单一来源)
# - 2026-04-15 16:00: 裁决 "RAG vs Fine-tuning" - 升级为 GREEN (多源印证)
```

### 版本回滚
```bash
# CLI (规划)
spine revert --to <commit_hash>
```

---

## 7. 待决策问题

1. **Git 仓库位置**：
   - 独立仓库？ (`backend/storage/git-repo`)
   - 复用当前 repo？ (`backend/.git`)

2. **Branch 策略**：
   - 单分支 (`main`)？
   - 双分支 (`main` + `evolution`)？

3. **用户权限**：
   - Web 界面是否需要登录系统？
   - 不同用户的知识库是否隔离？

---

## 8. 下一步行动

1. ✅ 完成本日志
2. ⏳ 实现四色置信度系统
3. ⏳ 实现 Git 版本管理
4. ⏳ CLI 逻辑迁移到 Backend
5. ⏳ FastAPI 路由层

---

**记录人**: Claude Code (Karpathy 模式)  
**最后更新**: 2026-04-15
