# SpineDoc (阅脊) — 逻辑刺客级文档审计引擎

专为审计合同、论文、法律文书等长文档设计。不是"跟 PDF 聊天"那种玩具——它提取逻辑脊梁、检测矛盾、溯源证据，最后给出有置信度的判决书。

```
Python 3.10+  |  飞书多维表格  |  MIT License
```

---

## 一、这玩意能干什么？

| 能力 | 本质 |
|------|------|
| **逻辑脊梁提取** | 从文档里抽出论证结构，不是简单的关键词匹配 |
| **LogicCourt 联邦法庭** | PLAN → 采集 → 审计 → 判决 → 演化，每一步可追溯 |
| **联网证人** | 本地证据不够？自动上网找，交叉验证 |
| **证据溯源** | 每个结论带原文引用和置信度颜色标记 |
| **主权演化** | AI 提演化方案，你核准了才落地，不做黑盒自动化 |
| **Git 版本追溯** | 语义切片有 Git 历史，能回滚 |

**适用场景**：合同审查找矛盾条款、论文审计查论证链条、法律文书比对证据链、招股书交叉验证数据。

---

## 二、快速开始（手工配置）

以下步骤从零开始，每步都确认了再做下一步。

### 2.1 系统要求

- Windows 10/11
- Python 3.10 或更高（[下载](https://www.python.org/downloads/)）
- 一个飞书企业账号
- 网络能访问飞书 API

### 2.2 克隆项目并创建虚拟环境

打开命令提示符（cmd），执行：

```batch
git clone <你的仓库地址> SpineDoc
cd SpineDoc

:: 创建虚拟环境（重要！不要把依赖装到全局）
python -m venv .venv

:: 激活虚拟环境
.venv\Scripts\activate

:: 安装依赖
pip install -r requirements.txt
```

看见 `(.venv)` 出现在行首说明环境激活成功。

如果 `pip install` 报错，检查 Python 版本是否 >= 3.10。

### 2.3 注册 API Key

你需要注册以下三个服务，**全部免费额度够用**：

| 服务 | 用途 | 怎么注册 |
|------|------|----------|
| **DeepSeek** | LLM 推理 | 打开 https://platform.deepseek.com/ → 注册 → 创建 API Key |
| **SiliconFlow** | 向量嵌入 + 视觉模型 | 打开 https://cloud.siliconflow.cn/ → 注册 → 创建 API Key |
| **智谱** | 联网搜索 | 打开 https://open.bigmodel.cn/ → 注册 → 创建 API Key |

**DeepSeek 特别注意**：
1. 注册后进入 API Keys 页面
2. 创建 API Key，复制以 `sk-` 开头的密钥
3. 建议使用 `deepseek-chat` 模型（性价比最高，支持 64K 上下文）
4. 如果希望使用最新模型，在 API 页面查看可用模型列表

### 2.4 下载 lark-cli

SpineDoc 需要 `lark-cli.exe` 来下载飞书文档和发送消息。

```batch
:: 访问 Releases 页面下载最新版
:: https://github.com/ConnectAI-E/Lark-CLI/releases

:: 下载后把 lark-cli.exe 放到项目根目录的 bin/ 文件夹
:: （没有就创建）
mkdir bin
:: 把下载的 lark-cli.exe 移动到 bin/ 目录下
```

飞书开放平台需要配置 App 权限。去 https://open.feishu.cn/app 创建企业自建应用：
1. 创建应用 → 填写名称
2. 「权限管理」→ 添加权限：
   - `bitable:app`（多维表格）
   - `drive:drive`（云文档）
   - `im:message`（消息推送）
   - `search:search`（搜索）
3. 「安全设置」→ 添加服务器 IP（生产环境需要）
4. 「凭证与基础信息」→ 拿到 `App ID` 和 `App Secret`
5. **发布应用**（否则 API 调用会返回权限错误）

### 2.5 创建飞书多维表格

#### 2.5.1 创建一个多维表格

1. 打开飞书 → 新建 → 多维表格
2. 命名为 `SpineDoc`（你可以随意命名）
3. 创建完成后，URL 里找到 `base_token`：
   - URL 格式：`https://xxx.feishu.cn/base/BASE_TOKEN?table=...`
   - 复制 `BASE_TOKEN` 这串字符

#### 2.5.2 创建数据表

你需要创建 4 个数据表。点击多维表格底部的 `+` 号新建表：

**表 1：文档表**（记录导入的文档）
| 字段名 | 字段类型 |
|--------|----------|
| 文件名 | 文本 |
| 文件哈希 | 文本 |
| 处理状态 | 文本（填入：PROCESSING / COMPLETED / FAILED） |
| 总页数 | 数字 |

**表 2：Chunk表**（存语义切片）
| 字段名 | 字段类型 |
|--------|----------|
| 正文内容 | 文本 |
| 逻辑摘要 | 文本 |
| 语义标签 | 多选 |
| 逻辑坐标 | 文本 |
| 逻辑面包屑 | 文本 |
| 逻辑指纹 | 文本 |
| 向量表征 | 文本 |
| Git版本 | 文本 |
| 物理页码 | 数字 |
| 元数据 | 文本 |
| 记忆ID | 文本 |
| 文档关联 | 关联 → 关联到「文档表」，单选 |
| 星系关联 | 关联 → 关联到「星系表」，多选 |
| 父级关联 | 关联 → 关联到本表（Chunk表），多选 |

创建「关联字段」时，系统会提示选择关联哪个表和是否多选，按上面表格配。

**表 3：脊梁表**（存文档目录结构）
| 字段名 | 字段类型 |
|--------|----------|
| 标题 | 文本 |
| 层级 | 数字 |
| 逻辑页码 | 数字 |
| 逻辑坐标 | 文本 |
| 文档关联 | 关联 → 关联到「文档表」，单选 |

**表 4：星系表**（跨文档聚类）
| 字段名 | 字段类型 |
|--------|----------|
| 星系名称 | 文本 |
| 重心向量 | 文本 |
| 锚点关键词 | 多选 |
| 成员总数 | 数字 |
| 描述 | 文本 |
| 锚点标签云 | 文本 |

**表 5：记忆表**（A-MEM 记忆层，可选）
| 字段名 | 字段类型 |
|--------|----------|
| 记忆ID | 文本 |
| 正文内容 | 文本 |
| 元数据 | 文本 |
| 向量表征 | 文本 |

创建完成后，每个表的 URL 里找到 `tblxxxxxxxx` 格式的 table_id。

自己核对一下表名和字段是否完全一致。大小写也要对上。

### 2.6 配置 .env 文件

在项目根目录创建 `.env` 文件，填入以下内容（尖括号替换成你的实际值）：

```ini
# ═══════════════════════════════════════════
# SpineDoc 环境配置（手工填写版）
# ═══════════════════════════════════════════

# ─── LLM（DeepSeek） ───
LLM_API_KEY=<你的 DeepSeek API Key>
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL_NAME=deepseek-chat     ← 模型名，可选 deepseek-chat / deepseek-reasoner

# ─── 向量嵌入（SiliconFlow） ───
EMBEDDING_API_KEY=sk-xxxxxxxxxxxx

# ─── 联网搜索（智谱） ───
ZHIPU_API_KEY=xxxxxxxxxx

# ─── 飞书集成 ───
FEISHU_APP_ID=cli_xxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxx
FEISHU_BITABLE_TOKEN=<Base Token>     ← 多维表格 URL 里的那串
FEISHU_BITABLE_TABLE_ID=tblxxxxxxxx   ← 文档表的 table_id
FEISHU_BITABLE_CHUNK_TABLE_ID=tblxxx ← Chunk表的 table_id
FEISHU_BITABLE_TOC_TABLE_ID=tblxxx   ← 脊梁表的 table_id
FEISHU_BITABLE_MEMORY_TABLE_ID=tblxxx← 记忆表的 table_id（和 FEISHU_BITABLE_CHUNK_TABLE_ID 可以填一样的值，共用 Chunk 表）
FEISHU_BITABLE_GALAXY_TABLE_ID=tblxxx← 星系表的 table_id
FEISHU_DEFAULT_CHAT_ID=oc_xxxxxxxxx  ← 通知消息发送到的群 ID（选填）

# ─── OCR 熔炼（选填，处理 PDF 需要） ───
ARK_API_KEY=
ARK_ENDPOINT=

# ─── Aily 桥接（选填） ───
FEISHU_AILY_TOKEN=
```

建好后用脚本来验证配置：

```batch
:: 激活虚拟环境（如果还没激活）
.venv\Scripts\activate

:: 验证配置完整性
python scripts/diagnose_config.py
```

如果报错说缺少某个配置项，回 2.5 和 2.6 对照填。

### 2.7 检查配置

所有配置完成后，用脚本验证：

```batch
python scripts/diagnose_config.py
```

如果报错说缺少某个配置项，回 2.5 和 2.6 对照填。

---

## 三、快速开始（一键脚本）

**⚠️ 自动脚本尚未完全验证，推荐优先用手工配置。**

如果仍想尝试：

```batch
:: 先确认 .venv 已激活，然后：
setup_env.bat
```

按提示填入 App ID 和 App Secret，询问「是否一键创建」时输入 `y`。
脚本会自动创建多维表格和数据表，写入 `.env` 和 manifest。

但之前提到的表字段仍建议对照 2.5.2 手动核对。

---

## 四、启动

### 4.1 启动 MCP Server

```batch
start_mcp.bat
```

看到 `MCP server running on port 7000` 说明启动成功。这个 Server 供 Aily 等 AI 代理调用，也用于调试。

如果不走 Aily，直接用命令行：

```batch
:: 导入文档
.venv\Scripts\python.exe spine_setup.py --ingest <你的文档.pdf>

:: 启动网页交互界面
.venv\Scripts\python.exe spine_setup.py --interactive
```

### 4.2 Aily 集成

详见 `spine_interaction/aily/SKILL.md` 和 `spinedoc-logic-assassin.skill`。

大致流程：
1. MCP Server 跑在公网可访问的地址（或配合 FRP 内网穿透）
2. 在 Aily 后台导入 `.skill` 文件作为 Agent 技能
3. 用户发消息 → Aily 调用 MCP 工具 → SpineDoc 执行审计 → 返回判决书

---

## 五、架构（几句话讲清楚）

```
用户输入
   │
   ▼
交互层：CLI / MCP / 飞书卡片
   │
   ▼
逻辑层：LogicCourt 联邦法庭
   ├─ PLAN      路由拆分
   ├─ HARVEST   取证（本地 + 联网）
   ├─ AUDIT     冲突审计 + 置信度计算
   ├─ SYNTHESIZE 判决签署
   └─ EVOLVE    演化提案（你核准才落地）
   │
   ▼
持久层：Bitable 表 + Git 版本控制 + A-MEM 记忆
```

每个阶段产出结构化的 `phase_log`，从推理到响应全链路可追踪。

---

## 六、常见问题

**Q：置信度全是 0.40？**
A：0.40 是单文档检索基准。多文档交叉验证能到 0.60-0.80，加联网证据能到 0.95。

**Q：文档导入后状态一直是 Processing？**
A：检查：Bitable Token 对不对、API Key 有没有额度、飞书应用是否已发布。

**Q：Chunk 表里的字段 API 报错？**
A：检查字段名是否完全一致，特别是「文档关联」这类关联字段的关联配置。

**Q：一键脚本报错？**
A：截图日志，提 Issue。目前脚本还没完全验证，手工配置更可靠。

---

## 许可证

MIT License
