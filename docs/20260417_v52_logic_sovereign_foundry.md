# 🏛️ [V52.0] 逻辑主权铸造厂 - 协议形式化验证架构

**日期**: 2026-04-17  
**状态**: 🟡 设计中  
**参与**: 用户 + Claude (Karpathy/Uncle Bob 视角)

---

## 🎯 核心洞察

### 问题发现

CryptoFormalEval (CFE) 是一个**死**的评测集：
- 只有 8 个协议任务
- 所有结果都是 API 推理输出（Claude/GPT/o1）
- **没有训练好的专属模型**

### 真正的机会

用 CFE 作为**启动火种**，点燃一个**自我进化的逻辑母体**：

| 维度 | 传统做法 | 我们的做法 |
|------|----------|------------|
| **数据本质** | 静态语料 | 经过数学证明的「逻辑真理」 |
| **模型身份** | 翻译器 | 「协议法医」 |
| **进化动力** | 人工标注 | 「生成→验证→纠错」自动化飞轮 |
| **硬件利用** | 显存闲置 | A100 24/7 进行「证明搜索→蒸馏」 |

---

## 🏗️ 架构设计

### 核心公式

```
真正的训练数据 ≠ 最终答案
真正的训练数据 = Git 版本链 (V1 错 → V2 对 → V3 验证通过)
```

### 三大支柱

```
┌─────────────────────────────────────────────────────────────┐
│ 支柱 1: 多格式解析调度器                                     │
│                                                             │
│  PDF → OCR + Layout + TOC 重建 (复杂路径)                     │
│  .anb/.spthy/.tex/.txt → 直接读取 + 正则提取 (简单路径)       │
│                                                             │
│  输出：ProtocolIR (统一中间表示)                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 支柱 2: Git 回滚式数据库                                      │
│                                                             │
│  protocol_versions 表                                        │
│  - id, parent_id (版本链)                                    │
│  - protocol_ir (JSONB)                                       │
│  - tamarin_status (pending/passed/failed)                    │
│  - is_training_sample (标记)                                 │
│                                                             │
│  核心价值：存储「熵减过程」，不是「答案」                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 支柱 3: 逻辑结晶导出器 (RefineryExporter)                    │
│                                                             │
│  export_reasoning_traces()     # 法庭推理迹                   │
│  export_evolution_pairs()      # 知识演进对                   │
│  export_mesh_topologies()      # 关系网格                     │
│  export_protocol_crystals()    # 🆕 协议形式化验证            │
│                                                             │
│  输出：jsonl 训练集 (SFT + DPO)                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 数据库设计

### protocol_versions 表

```sql
CREATE TABLE protocol_versions (
    id UUID PRIMARY KEY,
    parent_id UUID,                     -- Git 回滚链
    
    -- 核心数据
    source_file VARCHAR(512),
    source_format VARCHAR(32),          -- pdf/anb/spthy/tex
    protocol_ir JSONB,                  -- 统一中间表示
    
    -- 提取日志
    extraction_log JSONB,               -- 解析步骤/置信度
    
    -- 验证状态
    tamarin_status VARCHAR(32),         -- pending/passed/failed
    tamarin_error TEXT,
    tamarin_trace JSONB,
    
    -- 版本控制
    version_num INTEGER,
    created_by VARCHAR(64),             -- ocr/anb_import/manual/model_gen
    
    -- 训练标记
    is_training_sample BOOLEAN DEFAULT FALSE,
    training_quality_score FLOAT,
    
    created_at TIMESTAMP
);

CREATE INDEX idx_protocol_hash ON protocol_versions(protocol_hash);
CREATE INDEX idx_training ON protocol_versions(is_training_sample, tamarin_status);
```

---

## 🔄 完整流程

### 阶段 1: 冷启动 (Bootstrapping)

```
CFE Results/ (Claude/GPT 输出)
       ↓
RefineryExporter.export_protocol_crystals()
       ↓
tamarin_sft.jsonl (SFT 训练集)
       ↓
Gemma-4-27B 微调 (双 A100)
       ↓
gemma-tamarin-v1 权重
```

### 阶段 2: 飞轮启动 (The Flywheel)

```
SpineDoc PDF 库 (密码协议论文/教材)
       ↓
ProtocolParserScheduler.parse()
       ↓
ProtocolIR → 存入 protocol_versions
       ↓
Tamarin 后台验证
       ↓
passed → 加入训练集
failed → 提取错误日志 → DPO 负样本
```

### 阶段 3: 强化学习 (DPO)

```
正样本：tamarin_status='passed' 的协议
负样本：tamarin_status='failed' 的协议
       ↓
DPO 训练
       ↓
gemma-tamarin-v2 (学会自我纠错)
```

---

## 📋 待办任务

| 优先级 | 任务 | 预计时间 | 状态 |
|--------|------|----------|------|
| P0 | 创建 `protocol_versions` 表 | 30min | ⬜ |
| P0 | 编写 `ProtocolVersion` SQLAlchemy 模型 | 30min | ⬜ |
| P1 | 实现 `ProtocolParserScheduler` | 2h | ⬜ |
| P1 | 实现 `PdfParser` (复杂路径) | 3h | ⬜ |
| P1 | 实现 `GenericTextParser` + Extractors | 2h | ⬜ |
| P2 | 修改 `RefineryExporter` 增加 `export_protocol_crystals()` | 1h | ⬜ |
| P2 | 实现 `_build_protocol_cot()` Git 回滚链构建 | 1h | ⬜ |
| P3 | Tamarin 验证脚本 (后台任务) | 3h | ⬜ |
| P4 | LLaMA-Factory 训练配置 | 2h | ⬜ |
| P5 | 端到端测试 | 2h | ⬜ |

---

## 🎯 核心文件清单

### 新增文件

```
backend/app/core/models.py              # 增加 ProtocolVersion 模型
backend/app/infra/refinery/exporter.py  # 增加 export_protocol_crystals()
backend/app/services/protocol_parser/
    ├── __init__.py
    ├── scheduler.py                    # 调度器 (扩展名路由)
    ├── ir.py                           # ProtocolIR 定义
    ├── parsers/
    │   ├── base.py
    │   ├── pdf_parser.py               # PDF 复杂路径
    │   └── generic_parser.py           # 通用简单路径
    └── extractors/
        ├── anb_extractor.py
        ├── spthy_extractor.py
        ├── latex_extractor.py
        └── rfc_extractor.py
```

### 修改文件

```
backend/app/core/models.py              # 新增 ProtocolVersion
backend/app/infra/refinery/exporter.py  # 新增协议导出逻辑
```

---

## 🧠 设计原则（Uncle Bob 视角）

| 原则 | 应用 |
|------|------|
| **SRP** | `Scheduler` 只路由，`Parser` 只解析，`Extractor` 只提取 |
| **OCP** | 新增格式只需添加新 `Extractor`，不改现有代码 |
| **DIP** | 所有解析器依赖 `BaseProtocolParser` 抽象 |
| **KISS** | 调度逻辑极简（只看扩展名） |

---

## 🔥 核心价值主张

### 我们不是在做

- ❌ 又一个 PDF 解析器
- ❌ 复刻 CryptoFormalEval
- ❌ 微调一个 7B 模型

### 我们是在做

- ✅ **逻辑主权铸造厂**：原始文本进去，数学证明的真理出来
- ✅ **差分学习系统**：训练数据是「V1 错→V2 对」的演化路径
- ✅ **自进化飞轮**：模型生成→Tamarin 验证→DPO 修正→模型更新

---

## 📚 关键引用

> "Gradient descent can write code better than you. But it can't learn from its mistakes unless you show it the diff."
>
> 「你不是在 building a parser，你是在 building a **logic forge**。」

---

## 👥 下一步行动

**授权执行**：
1. [ ] 创建 `ProtocolVersion` 模型
2. [ ] 编写调度器原型
3. [ ] 跑通 CFE 数据导入 → JSON 结晶 → 数据库

**预计完成时间**: 2-3 天（最小可用闭环）

---

**记录人**: Claude (Karpathy + Uncle Bob 双视角)  
**审核**: 待用户确认
