# SpineDoc 虚拟环境部署规划

## 问题背景
- 当前 `spine` 命令在系统 Python 中指向旧项目（Spine-open）
- 虚拟环境 `.venv` 中有正确的依赖和配置，但用户无法直接使用
- 需要让用户像普通 CLI 工具一样直接输入 `spine` 就能使用

---

## 解决方案对比

### 方案 A：全局安装 spine 命令（推荐 ⭐）
**原理**：在虚拟环境中执行 `pip install --user -e .`，将 `spine` 命令安装到用户全局 PATH

**优点**：
- 用户体验最佳，直接输入 `spine` 即可
- 无需修改现有工作流
- 符合 Python 应用分发惯例

**缺点**：
- 全局安装会覆盖之前 `Spine-open` 的 `spine` 命令
- 如果虚拟环境被删除，命令会失效

**实施步骤**：
1. 在 `.venv` 中执行：`.venv\Scripts\pip install --user -e .`
2. 验证：在任意目录执行 `spine --help`
3. 更新 README 文档

---

### 方案 B：提供启动脚本
**原理**：创建 `.bat` 或 `.ps1` 脚本，自动激活虚拟环境并执行命令

**优点**：
- 不需要全局安装
- 虚拟环境完全独立

**缺点**：
- 用户需要记住使用 `spine.bat` 而不是 `spine`
- Windows 执行策略可能阻止 `.ps1` 脚本

**实施步骤**：
1. 创建 `spine.bat`：
   ```batch
   @echo off
   call %~dp0.venv\Scripts\activate.bat
   spine %*
   ```
2. 将脚本目录加入 PATH

---

### 方案 C：使用 Python 启动器
**原理**：创建 `spine.py` 启动器，用户通过 `python spine.py` 运行

**优点**：
- 最简单，无需安装

**缺点**：
- 用户输入变长（`python spine.py` vs `spine`）
- 体验较差

---

## 推荐方案：方案 A（全局安装）

### 详细实施计划

#### Step 1: 清理现有安装
```bash
pip uninstall spine-cli -y  # 卸载系统 Python 的旧版本
```

#### Step 2: 在虚拟环境中安装到全局
```bash
.venv\Scripts\pip install --user -e .
```

#### Step 3: 验证安装
```bash
spine --help  # 应该显示 Spine-close 的帮助
```

#### Step 4: 更新文档
在 README 中添加：
```markdown
## 安装

### 开发者模式（推荐）
git clone <repo>
cd Spine-close
.venv\Scripts\activate
pip install -e .

### 用户模式（一次性安装）
.venv\Scripts\pip install --user -e .
# 之后可直接使用 spine 命令
```

---

## 风险与缓解

| 风险 | 缓解措施 |
|------|----------|
| 虚拟环境删除导致命令失效 | 在文档中警告用户不要删除 `.venv` |
| 与系统 Python 依赖冲突 | 使用 `--user` 安装到用户目录，避免全局污染 |
| numpy/torch 版本冲突 | 锁定 `requirements.txt` 版本 |

---

## 后续任务

1. ✅ 修复 `pyproject.toml` 包声明（已完成）
2. ⏳ 执行方案 A 安装
3. ⏳ 全链路测试（入库 → 单文档问答 → 多文档问答 → Git 回滚 → 知识库更新）
4. ⏳ 更新 README 文档
5. ⏳ 推送代码到远程仓库

---

## 全链路测试清单

- [ ] **步骤 1**: 检查数据库状态（已有 9 篇文档）
- [ ] **步骤 2**: SM4.pdf 入库（`spine ingest ceshi_ocr/SM4.pdf`）
- [ ] **步骤 3**: 单文档问答（`spine ask "SM4 的主要贡献是什么" -d <SM4_ID>`）
- [ ] **步骤 4**: 多文档问答（`spine ask "对比 SM4 和 logic_mirror 的方法" -d all`）
- [ ] **步骤 5**: Git 回滚测试（`spine git history <chunk_id>` → `spine git revert`）
- [ ] **步骤 6**: 知识库更新测试（`spine ask "xxx" --online`）

---

*创建时间：2026-04-16*
