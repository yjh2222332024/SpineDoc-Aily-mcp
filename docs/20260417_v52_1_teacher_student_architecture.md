# 🏛️ [V52.1] 备课老师 + 小学生架构 - 多智能体集群设计

**日期**: 2026-04-17  
**状态**: 🟡 设计中  
**参与**: 用户 + Claude

---

## 🎯 核心洞察

### Gemma 4 的真正定位

**不是**「执行者」（写代码、生成引理、调试）

**而是**「备课老师」：
1. 理解逻辑（这个协议的核心难点在哪）
2. 备课（拆解成多个子任务）
3. 分发（每个任务交给对应的小学生）
4. 批改（整合小学生的作业，检查对错）

### 小学生的定位

**不是**「辅助模型」

**而是**「专精执行者」：
- 1.5B 语法小学生：只学 `.spthy` 语法骨架
- 1.5B 引理小学生：只学引理设计
- 1.5B 调试小学生：只学解读 Tamarin 报错

---

## 🏗️ 架构设计

```
┌─────────────────────────────────────────────────────────────┐
│  Gemma 4-27B (备课老师)                                      │
│                                                             │
│  输入：SpineDoc 吐出的原始知识结晶                            │
│       (ProtocolIR + Git 版本链 + Tamarin 验证状态)             │
│                                                             │
│  训练目标：                                                  │
│  - 学会理解协议逻辑（难点在哪、易错点在哪）                   │
│  - 学会拆解任务（这个协议需要哪些步骤）                       │
│  - 学会批改作业（整合小学生输出，检查一致性）                 │
│                                                             │
│  推理时职责：                                                │
│  1. 读协议 → 输出「任务拆解列表」                             │
│  2. 分发任务 → 调用对应小学生 LoRA                            │
│  3. 整合结果 → 输出最终答案                                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
         ┌──────────────────┼──────────────────┐
         ↓                  ↓                  ↓
   ┌──────────┐       ┌──────────┐       ┌──────────┐
   │ 1.5B 语法  │       │ 1.5B 引理  │       │ 1.5B 调试  │
   │ 小学生    │       │ 小学生    │       │ 小学生    │
   └──────────┘       └──────────┘       └──────────┘
         ↓                  ↓                  ↓
   只学语法骨架         只学引理设计         只学报错修正
   (IR → .spthy)     (IR+ 属性→引理)      (错误 + 报错→修正)
```

---

## 📊 训练数据设计

### Gemma 4 备课老师（学会理解 + 拆解）

```json
{
  "instruction": "请分析这个协议并拆解任务",
  "input": "Protocol: Needham-Schroeder Symmetric Key\n\nA -> S: A, B, Na\nS -> A: {Na, B, Kab, {Kab, A}Kbs}Kas\nA -> B: {Kab, A}Kbs\n...",
  "analysis": "这是一个对称密钥认证协议。核心难点：1. Kab 的保密性 2. A 和 B 的相互认证 3. Na/Nb 的新鲜性。易错点：Lowe 攻击已知漏洞...",
  "task_decomposition": [
    {"task_id": 1, "type": "syntax", "instruction": "生成.spthy 骨架，包含角色 A/B/S 和消息流"},
    {"task_id": 2, "type": "lemma", "instruction": "设计 Secrecy 和 Authentication 引理"},
    {"task_id": 3, "type": "verify", "instruction": "运行 Tamarin 验证，检查是否有攻击"}
  ]
}
```

**数据源**：SpineDoc 数据库中的 `protocol_versions` 表
- 只选 `tamarin_status='passed'` 的样本
- 提取 `protocol_ir` + `extraction_log` + Git 版本链

---

### 1.5B 语法小学生（专精语法）

```json
{
  "instruction": "根据协议 IR 生成.spthy 骨架",
  "input": "Participants: A, B, S\nKnowledge: A=[Kas], B=[Kbs], S=[Kas, Kbs]\nMessages: 1. A -> S: A, B, Na\n2. S -> A: {Na, B, Kab, {Kab, A}Kbs}Kas\n...",
  "output": "theory Needham_Schroeder_Symmetric begin\nbuiltins: symmetric-encryption\n\nrule Asymmetric_key_setup:\n  [ Fr(~f) ] --> [ !Sk($A, sk(~f)), !Pk($A, pk(~f)) ]\n...\nend"
}
```

**数据源**：CFE 的 `Input/` + `[id]_solution/` 配对

---

### 1.5B 引理小学生（专精引理设计）

```json
{
  "instruction": "设计 Freshness 引理",
  "input": "协议中有两个 Fresh 值：Na (由 A 生成), Nb (由 B 生成)",
  "output": "lemma freshness_Na:\n  \"All a b na #i. K(<a, b, na>) @ i ==> not (Ex #j. K(na) @ j & j < i)\"\n\nlemma freshness_Nb:\n  \"All a b nb #i. K(<a, b, nb>) @ i ==> not (Ex #j. K(nb) @ j & j < i)\""
}
```

**数据源**：CFE 的 `[id]_solution/*.spthy` 中的 `lemma` 部分提取

---

### 1.5B 调试小学生（专精报错解读）

```json
{
  "instruction": "根据 Tamarin 报错修正代码",
  "input": "错误代码：rule m1_A: [ St_init_A(A, Ks, M) ] --[ ]-> [ Out(Na) ]\n\nTamarin 报错：\"Variable Na is not bound in any premise\"",
  "output": "修正后：rule m1_A: [ St_init_A(A, Ks, M), Fr(~Na) ] --[ ]-> [ Out(~Na) ]"
}
```

**数据源**：Tamarin 验证失败案例 + 人工修正记录

---

## 🔄 训练策略

| 模型 | 参数量 | 数据源 | 训练方式 | 显存占用 | 预计时间 |
|------|--------|--------|----------|----------|----------|
| **Gemma 4 备课老师** | 27B | SpineDoc ProtocolIR + Git 历史 | 全参数 SFT | 双 A100 (80GB×2) | 2-3 天 |
| **1.5B 语法小学生** | 1.5B | CFE Input→Solution 配对 | LoRA 微调 | 单 A100 (16GB) | 4 小时 |
| **1.5B 引理小学生** | 1.5B | CFE Lemma 提取配对 | LoRA 微调 | 单 A100 (16GB) | 4 小时 |
| **1.5B 调试小学生** | 1.5B | Tamarin 失败→修正配对 | LoRA 微调 | 单 A100 (16GB) | 4 小时 |

---

## 🚀 推理流程

```python
class TamarinTeacherStudentCluster:
    def __init__(self):
        # 备课老师 (双 A100)
        self.teacher = Gemma_4_27B
        
        # 小学生 (单 A100, LoRA 切换)
        self.students = {
            "syntax": load_lora("syntax_1.5B.pt"),
            "lemma": load_lora("lemma_1.5B.pt"),
            "debug": load_lora("debug_1.5B.pt"),
        }
    
    async def run(self, protocol_ir) -> Dict:
        # 1. 备课老师理解协议
        analysis = self.teacher.generate(
            prompt=self._build_analysis_prompt(protocol_ir)
        )
        
        # 2. 备课老师拆解任务
        tasks = self.teacher.generate(
            prompt=self._build_decompose_prompt(analysis)
        )
        
        # 3. 分发任务给小学生
        results = {}
        for task in tasks:
            student_type = self._route_task(task)  # 路由到对应小学生
            result = self.teacher.generate(
                prompt=self._build_task_prompt(task),
                lora=self.students[student_type]  # 切换小学生模式
            )
            results[task.id] = result
        
        # 4. 备课老师整合结果
        final = self.teacher.generate(
            prompt=self._build_merge_prompt(results)
        )
        
        return {
            "analysis": analysis,
            "tasks": tasks,
            "student_results": results,
            "final_output": final,
        }
```

---

## 📈 反哺飞轮

```
每次 Tamarin 验证完成:
    ↓
Gemma 4 分析：「这次是引理设计错了」or「这次是语法错了」
    ↓
把失败案例加入对应小学生的训练集
    ↓
每周重新训练 LoRA 适配器
    ↓
小学生变强了 → Gemma 4 下次分发更准确
```

---

## 🎯 上下文管理

| 阶段 | 输入长度 | 输出长度 | 总上下文 |
|------|----------|----------|----------|
| **Gemma 4 分析** | 协议 IR (~500 tokens) | 分析 + 任务拆解 (~800 tokens) | ~1.3K |
| **小学生执行** | 单个任务 (~300 tokens) | 专精输出 (~500 tokens) | ~800 tokens |
| **Gemma 4 整合** | 所有小学生结果 (~2K tokens) | 最终答案 (~500 tokens) | ~2.5K |

**关键**：小学生只处理自己的任务，上下文不会爆炸。

---

## 📋 待办任务

| 优先级 | 任务 | 预计时间 | 状态 |
|--------|------|----------|------|
| P0 | 创建 `protocol_versions` 表 | 30min | ⬜ |
| P0 | 编写 `ProtocolVersion` SQLAlchemy 模型 | 30min | ⬜ |
| P1 | 设计 Gemma 4 训练数据提取脚本 | 2h | ⬜ |
| P1 | 设计小学生 LoRA 训练数据格式 | 2h | ⬜ |
| P2 | 实现 `ProtocolParserScheduler` | 2h | ⬜ |
| P3 | Gemma 4 全参数 SFT 训练配置 | 3h | ⬜ |
| P4 | 小学生 LoRA 训练配置 | 2h | ⬜ |
| P5 | 端到端测试 | 2h | ⬜ |

---

## 🧠 设计原则

| 原则 | 应用 |
|------|------|
| **关注点分离** | 备课老师理解逻辑，小学生执行专精任务 |
| **上下文隔离** | 每个小学生只看到自己的任务，不爆炸 |
| **可独立进化** | 某个小学生弱了，只训那个，不影响其他 |
| **反哺飞轮** | 失败案例自动加入训练集，持续变强 |

---

## 🔥 核心价值

### 我们不是在做

- ❌ 单一大模型 All-in-One
- ❌ 复刻 CryptoFormalEval
- ❌ 微调一个什么都会但什么都不精的模型

### 我们是在做

- ✅ **备课老师**：学会理解逻辑 + 拆解任务
- ✅ **小学生集群**：每个只学一样，但学到极致
- ✅ **反哺飞轮**：失败案例自动变成训练数据

---

## 👥 下一步行动

**授权执行**：
1. [ ] 创建 `ProtocolVersion` 模型
2. [ ] 设计 Gemma 4 训练数据提取脚本
3. [ ] 跑通 CFE 数据导入 → JSON 结晶 → 数据库

**预计完成时间**: 2-3 天（最小可用闭环）

---

**记录人**: Claude  
**审核**: 待用户确认
