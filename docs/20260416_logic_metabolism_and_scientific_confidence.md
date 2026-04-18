# 📜 SpineDoc 逻辑代谢与科学置信度协议 (V9.2) (2026-04-16)

## 1. 核心挑战：魔法数字的非法性
在专业的逻辑审计系统中，任何硬编码的权重（如 0.9, 0.8）都是对“客观真实”的人为干扰。我们必须建立一套能够**从数据演进中自发产生**的量化体系。

## 2. 核心公式：自适应逻辑代谢 ($\tau$)
我们引入 **“逻辑代谢率”** ($\tau$) 概念，用于量化不同领域知识的更新速度。

### A. 代谢周期计算
*   **数据源**：`ChunkRevision` (Git Ledger)。
*   **算法**：$\tau = \frac{\sum (T_{new} - T_{old})}{N}$。
*   **物理语义**：该星系（Galaxy）内，平均多久会发生一次知识纠偏或事实覆盖。

### B. 科学衰减模型 (Exponential Decay)
置信度不再是瞬间折半，而是随时间平滑坍缩：
$$W_{recency} = e^{-\frac{\Delta t}{\tau}}$$
*   **$\Delta t$**：新旧证据的时间差。
*   **$\tau$**：自适应领域周期。

## 3. 约束条件：语义位移过滤 (Semantic Displacement)
*   **逻辑**：只有当新旧证据的向量余弦相似度 $Sim_{semantic} > 0.85$ 时，才触发时间衰减。
*   **意义**：如果两个 Chunk 在讨论不同的子命题，它们是**互补**关系，即便时间跨度大也不应降权。

## 4. 架构实现：`SovereignMassAllocator`
建立独立的分配器类，实现以下原子逻辑：

| 维度 | 输入信号 | 计算逻辑 |
| :--- | :--- | :--- |
| **主权分** | `Authoritative_Domains.json` | 基础 Belief 分配 (arXiv: 0.95, Blog: 0.4)。 |
| **时效分** | `Git_Ledger_Velocity` | 动态 $\tau$ 指数衰减。 |
| **冲突分** | `EvidenceFusionEngine` | D.S. 理论计算冲突因子 K 并执行物理坍缩。 |

## 5. 对 1.5B 专家训练的意义
*   **内化时间感**：训练模型在推理时，能够感知上下文的时间戳，自发产生对旧知识的怀疑感。
*   **数学一致性**：模型输出的 Confidence 将具备统计学层面的可解释性，符合 **Conformal Prediction** 的分布保证。

---

**记录人：System Agent (Acting as Karpathy & Uncle Bob)**
**状态：协议已定，准备物理实现 `GitVelocityStats`。**
