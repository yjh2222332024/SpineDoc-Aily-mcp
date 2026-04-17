# 📜 互联网知识净化与虚拟脊梁协议 (2026-04-16)

## 1. 核心挑战：异构数据的“主权危机”
联网数据（HTML/Markdown）缺乏 PDF 的物理页码约束，且充斥着 SEO 噪音（注册、广告、导航）。若直接引入联邦法庭，将稀释本地主权并污染 1.5B 模型的训练结晶。

## 2. 虚拟物理坐标 (Virtual Physical Coordinates)
为了实现“寻址平权”，我们为非 PDF 数据建立一套虚拟坐标系统：
*   **映射规则**：将 Markdown 的标题层级 (`H1`, `H2`, `H3`) 强制映射为 **虚拟页码 (V-Page)**。
    *   `# Title` -> `V-P1`
    *   `## Section` -> `V-P2`
*   **统一寻址**：所有联网证据必须符合 `spine://internet/{domain}/{content_hash}/vp{page}` 格式。
*   **价值**：使 1.5B 模型在训练时，能够对本地与网络数据使用统一的“空间逻辑定位”算法。

## 3. 三级净化系统 (The Triple Sieve)
所有联网证词在进入法庭前，必须通过物理级去噪。

### 第一级：逻辑密度过滤 (Entropy Check)
*   **机制**：计算 `核心关键词数 / 总字符数`。
*   **纪律**：逻辑密度低于阈值（如 10%）的分片，判定为“低熵废话”，直接物理剔除。

### 第二级：语义脚手架切除 (Boilerplate Removal)
*   **黑名单**：建立 `WEB_NOISE_PATTERNS`，包含：
    *   *导航类*：登录、注册、订阅、跳转、关于我们。
    *   *SEO 类*：点击查看、推荐阅读、版权所有、Cookie 政策。
*   **动作**：在调用 `StructuralSplitter` 前，执行正则级与结构级的切除。

### 第三级：主权分类 (Sovereignty Classification)
*   **判定**：利用 0.1 度的轻量级模型判定分片属性。
*   **分类**：`FACTUAL` (事实) | `GUIDE` (操作指南) | `NOISE` (噪音)。
*   **结果**：只有 `FACTUAL` 和 `GUIDE` 允许进入 Git Ledger 记录，`NOISE` 绝不入库。

## 4. 架构集成：`KnowledgeSieve` 服务
在 `internet_witness.py` 中引入专门的净化器类，确保“在 Ingest 的那一刻就拒之门外”。

```python
class KnowledgeSieve:
    """职责：将无序的网络流精炼为有序的逻辑结晶"""
    def purify(self, raw_chunks):
        # 1. 虚拟坐标生成 (Virtual ISR)
        # 2. 语义脚手架切除
        # 3. 逻辑密度校验
        return clean_logic_chunks
```

## 5. 对微调的意义
*   **零幻觉语料**：通过净化系统，我们保证了 1.5B 模型学到的每一个 Token 都是“高压逻辑”。
*   **纠错能力**：Git Ledger 记录了“网页噪音被识别并剔除”或“旧网页被新网页演进”的过程，这是训练模型“批判性思维”的极品素材。

---

**记录人：System Agent (Acting as Karpathy & Uncle Bob)**
**状态：协议已定，准备实施。**
