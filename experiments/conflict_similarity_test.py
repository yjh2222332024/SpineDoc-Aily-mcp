"""
🧪 冲突类型与向量相似度相关性实验
==================================
目的：验证"真正冲突"与"同名异义"的向量相似度分布差异，找出最佳裁决阈值。

实验设计 (Karpathy, 2026-04-17):
1. 收集 20-30 个"真正冲突"样本对（同一主题内的逻辑矛盾）
2. 收集 20-30 个"同名异义"样本对（不同主题的语义漂移）
3. 计算每对的余弦相似度
4. 画分布直方图，找分界线

假设:
- 真正冲突：相似度 0.5-0.8
- 同名异义：相似度 0.1-0.3
"""

import asyncio
import json
from typing import List, Tuple, Dict
import httpx
from backend.app.core.config import settings

# ============== 实验样本 ==============

# 🔴 真正冲突样本对（同一主题内的逻辑矛盾）
TRUE_CONFLICTS = [
    {
        "name": "安装方式冲突 - macOS",
        "chunk_a": "在 macOS 上安装 Tamarin：使用 Homebrew 一键安装 `brew install tamarin-prover`",
        "chunk_b": "在 macOS 上安装 Tamarin：必须从源码编译，Homebrew 版本已过时"
    },
    {
        "name": "Python 版本要求",
        "chunk_a": "Tamarin 需要 Python 3.8 或更高版本才能运行",
        "chunk_b": "Tamarin 仅支持 Python 3.6，不兼容 Python 3.7+"
    },
    {
        "name": "依赖项冲突 - Maude 版本",
        "chunk_a": "Maude 2.7.1 是最低要求，建议使用 3.0 版本",
        "chunk_b": "Maude 必须使用 2.7.1 版本，3.0 存在兼容性问题"
    },
    {
        "name": "运行模式冲突",
        "chunk_a": "启动交互式模式：`tamarin-prover interactive file.spthy`，访问 localhost:3001",
        "chunk_b": "启动交互式模式：`tamarin-prover --gui file.spthy`，自动打开浏览器窗口"
    },
    {
        "name": "证明策略冲突",
        "chunk_a": "使用 --prove 自动证明所有引理，适合简单协议",
        "chunk_b": "--prove 标志仅适用于部分引理，复杂协议必须手动交互式证明"
    },
    {
        "name": "内存需求冲突",
        "chunk_a": "Tamarin 推荐至少 4GB 内存运行大型协议验证",
        "chunk_b": "Tamarin 在 2GB 内存下即可运行，但证明速度会显著降低"
    },
    {
        "name": "图形输出冲突",
        "chunk_a": "安装 GraphViz 后可生成证明过程的可视化图",
        "chunk_b": "图形输出功能依赖 GraphViz 2.40+，旧版本无法渲染"
    },
    {
        "name": "WSL 支持冲突",
        "chunk_a": "WSL2 完全支持 Tamarin 运行，推荐使用 Ubuntu 20.04",
        "chunk_b": "WSL 存在已知图形界面问题，建议直接在 Windows 使用预编译版本"
    },
    {
        "name": "编译时间冲突",
        "chunk_a": "从源码编译 Tamarin 需要约 30-60 分钟",
        "chunk_b": "从源码编译 Tamarin 在高性能机器上仅需 10-15 分钟"
    },
    {
        "name": "协议模型冲突 - NS 协议",
        "chunk_a": "Needham-Schroeder 协议在 Tamarin 中验证通过，无已知攻击",
        "chunk_b": "Needham-Schroeder 协议存在 Lowe 攻击，Tamarin 可自动发现"
    },
    {
        "name": "观测等价性冲突",
        "chunk_a": "观测等价性分析使用 --diff 模式，比较两个协议的输出差异",
        "chunk_b": "观测等价性必须使用单独的 obs-eq 命令，--diff 仅用于调试"
    },
    {
        "name": "引理语法冲突",
        "chunk_a": "引理使用 `lemma` 关键字定义，后跟名称和公式",
        "chunk_b": "引理必须使用 `Lemma` 首字母大写，小写会导致解析错误"
    },
    {
        "name": "规则前提冲突",
        "chunk_a": "规则前提中的事实使用线性逻辑，使用后自动消耗",
        "chunk_b": "规则前提中的事实默认持久化，需要使用 `!` 标记才会消耗"
    },
    {
        "name": "时间戳语义冲突",
        "chunk_a": "时间戳 @i 表示事件在时间点 i 发生，i 是自然数",
        "chunk_b": "时间戳是可选的，省略时 Tamarin 自动分配最小可用时间"
    },
    {
        "name": "攻击迹输出冲突",
        "chunk_a": "找到攻击时，Tamarin 输出完整的攻击迹（trace）",
        "chunk_b": "找到攻击时，Tamarin 只输出是否可达，不显示详细迹"
    }
]

# 🔵 同名异义样本对（不同主题的语义漂移）
SAME_NAME_DIFF_TOPIC = [
    {
        "name": "Tamarin - 工具 vs 动物",
        "chunk_a": "Tamarin Prover 是一款用于安全协议形式化验证的工具，支持保密性和认证性分析",
        "chunk_b": "赤掌獠狨（Saguinus midas），别名红掌绢猴，分布于法属圭亚那，体长 20-28 厘米"
    },
    {
        "name": "Tamarin - 工具 vs JS 引擎",
        "chunk_a": "Tamarin 使用 Haskell 编写，依赖 Maude 推理引擎进行符号分析",
        "chunk_b": "Tamarin 是 Mozilla 的 ActionScript 虚拟机，后捐赠给 Adobe，是 JavaScript 引擎"
    },
    {
        "name": "Tamarin - 工具 vs 遗传学教材",
        "chunk_a": "运行 tamarin-prover interactive 后访问 localhost:3001 使用图形界面",
        "chunk_b": "Tamarin R H. Principles of Genetics, 7th ed. Boston: McGraw-Hill, 2002"
    },
    {
        "name": "RAG - 检索增强生成 vs 音乐流派",
        "chunk_a": "RAG (Retrieval-Augmented Generation) 通过向量检索增强 LLM 的上下文窗口",
        "chunk_b": "Rag 是一种印度传统音乐调式系统，每个 Rag 表达特定的情感和氛围"
    },
    {
        "name": "Agent - AI 代理 vs 特工",
        "chunk_a": "AI Agent 通过工具调用和环境交互完成复杂任务，支持多轮规划",
        "chunk_b": "秘密特工使用加密通信渠道传递情报，避免被敌对势力拦截"
    },
    {
        "name": "Transformer - 模型 vs 电力设备",
        "chunk_a": "Transformer 使用自注意力机制处理序列数据，摒弃了递归结构",
        "chunk_b": "变压器用于改变交流电的电压等级，通过电磁感应原理工作"
    },
    {
        "name": "Prompt - 提示词 vs 提词器",
        "chunk_a": "Prompt Engineering 通过设计输入文本来引导 LLM 生成特定输出",
        "chunk_b": "戏剧演出中提词员在演员忘词时低声提示下一句台词"
    },
    {
        "name": "Chain - 区块链 vs 链条",
        "chunk_a": "区块链通过工作量证明和默克尔树保证交易不可篡改",
        "chunk_b": "自行车链条需要定期润滑以减少磨损，延长使用寿命"
    },
    {
        "name": "Model - 机器学习模型 vs 模特",
        "chunk_a": "模型训练通过反向传播算法更新权重，最小化损失函数",
        "chunk_b": "时装模特在 T 台展示设计师最新系列，需要保持专业姿态"
    },
    {
        "name": "Fine-tuning - 微调模型 vs 精细调整",
        "chunk_a": "Fine-tuning 在预训练模型基础上针对特定任务进行有监督训练",
        "chunk_b": "小提琴琴弦需要精细调整张力，确保音准精确到音分"
    },
    {
        "name": "Inference - 推理 vs 推断",
        "chunk_a": "推理阶段模型执行前向传播，将输入 token 映射为输出概率分布",
        "chunk_b": "侦探通过现场证据推断凶手的作案手法和逃跑路线"
    },
    {
        "name": "Token - 词元 vs 代币",
        "chunk_a": "Tokenization 将文本切分为模型可处理的子词单元，如 'playing' → 'play' + 'ing'",
        "chunk_b": "赌场代币可在特定机器上兑换现金，需要保留购买凭证"
    },
    {
        "name": "Attention - 注意力机制 vs 注意力",
        "chunk_a": "多头注意力允许模型同时关注输入序列的不同位置，捕获长距离依赖",
        "chunk_b": "儿童注意力缺陷多动障碍 (ADHD) 表现为难以集中精神和过度活跃"
    },
    {
        "name": "Layer - 神经网络层 vs 图层",
        "chunk_a": "Transformer 编码器由 12 层自注意力和前馈网络堆叠而成",
        "chunk_b": "Photoshop 图层可独立调整透明度、混合模式和位置"
    },
    {
        "name": "Embedding - 词嵌入 vs 嵌入物体",
        "chunk_a": "词嵌入将离散词汇映射到连续向量空间，语义相近的词向量距离更近",
        "chunk_b": "子弹嵌入墙壁后变形，法医通过弹道分析确定枪支型号"
    }
]

# ============== 实验工具 ==============

async def get_embedding(text: str) -> List[float]:
    """调用本地 Embedding API 获取向量"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 使用本地配置的 Embedding 服务
            payload = {
                "input": [text],
                "model": settings.EMBEDDING_MODEL_NAME
            }
            headers = {
                "Authorization": f"Bearer {settings.EMBEDDING_API_KEY}",
                "Content-Type": "application/json"
            }
            resp = await client.post(
                f"{settings.EMBEDDING_BASE_URL.rstrip('/')}/embeddings",
                json=payload,
                headers=headers
            )
            resp.raise_for_status()
            return resp.json()["data"][0]["embedding"]
        except Exception as e:
            print(f"⚠️ 向量化失败：{e}")
            # 兜底：返回零向量
            return [0.0] * settings.EMBEDDING_DIMENSION

def cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """计算余弦相似度"""
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)

async def compute_pair_similarity(pair: Dict) -> Tuple[str, float]:
    """计算单个样本对的相似度"""
    vec_a = await get_embedding(pair["chunk_a"])
    vec_b = await get_embedding(pair["chunk_b"])
    sim = cosine_similarity(vec_a, vec_b)
    return (pair["name"], sim)

async def run_experiment():
    """运行完整实验"""
    print("=" * 70)
    print("🧪 冲突类型与向量相似度相关性实验")
    print("=" * 70)

    # 1. 计算真正冲突的相似度
    print("\n🔴 计算真正冲突样本对的相似度...")
    true_conflict_sims = []
    for i, pair in enumerate(TRUE_CONFLICTS):
        name, sim = await compute_pair_similarity(pair)
        true_conflict_sims.append(sim)
        print(f"  [{i+1:2d}] {name}: {sim:.4f}")

    # 2. 计算同名异义的相似度
    print("\n🔵 计算同名异义样本对的相似度...")
    same_name_sims = []
    for i, pair in enumerate(SAME_NAME_DIFF_TOPIC):
        name, sim = await compute_pair_similarity(pair)
        same_name_sims.append(sim)
        print(f"  [{i+1:2d}] {name}: {sim:.4f}")

    # 3. 统计分析
    print("\n" + "=" * 70)
    print("📊 统计分析")
    print("=" * 70)

    import statistics

    tc_mean = statistics.mean(true_conflict_sims)
    tc_std = statistics.stdev(true_conflict_sims) if len(true_conflict_sims) > 1 else 0
    tc_min = min(true_conflict_sims)
    tc_max = max(true_conflict_sims)
    tc_median = statistics.median(true_conflict_sims)

    sn_mean = statistics.mean(same_name_sims)
    sn_std = statistics.stdev(same_name_sims) if len(same_name_sims) > 1 else 0
    sn_min = min(same_name_sims)
    sn_max = max(same_name_sims)
    sn_median = statistics.median(same_name_sims)

    print(f"""
🔴 真正冲突 (n={len(true_conflict_sims)}):
   均值：{tc_mean:.4f} ± {tc_std:.4f}
   中位数：{tc_median:.4f}
   范围：[{tc_min:.4f}, {tc_max:.4f}]

🔵 同名异义 (n={len(same_name_sims)}):
   均值：{sn_mean:.4f} ± {sn_std:.4f}
   中位数：{sn_median:.4f}
   范围：[{sn_min:.4f}, {sn_max:.4f}]

📈 两类分布差异：{tc_mean - sn_mean:.4f}
""")

    # 4. 找出最佳阈值
    print("\n🔍 寻找最佳分类阈值...")

    all_samples = (
        [(s, 1) for s in true_conflict_sims] +  # 1 = 真正冲突
        [(s, 0) for s in same_name_sims]        # 0 = 同名异义
    )
    all_samples.sort(key=lambda x: x[0])  # 按相似度排序

    best_threshold = 0.5
    best_accuracy = 0.0

    for threshold in [i / 100 for i in range(10, 90)]:
        # 简化分类：相似度 > threshold → 真正冲突，否则 → 同名异义
        correct = 0
        for sim, label in all_samples:
            predicted = 1 if sim > threshold else 0
            if predicted == label:
                correct += 1
        accuracy = correct / len(all_samples)

        if accuracy > best_accuracy:
            best_accuracy = accuracy
            best_threshold = threshold

    print(f"""
最佳阈值：{best_threshold:.2f}
分类准确率：{best_accuracy:.2%}

裁决规则：
- 相似度 > {best_threshold:.2f} → 视为"真正冲突"，需要 Moderator 裁决
- 相似度 ≤ {best_threshold:.2f} → 视为"同名异义"，直接排除，不进入裁决
""")

    # 5. 保存结果
    results = {
        "true_conflicts": {
            "count": len(true_conflict_sims),
            "mean": tc_mean,
            "std": tc_std,
            "median": tc_median,
            "min": tc_min,
            "max": tc_max,
            "samples": true_conflict_sims
        },
        "same_name_diff_topic": {
            "count": len(same_name_sims),
            "mean": sn_mean,
            "std": sn_std,
            "median": sn_median,
            "min": sn_min,
            "max": sn_max,
            "samples": same_name_sims
        },
        "best_threshold": best_threshold,
        "best_accuracy": best_accuracy
    }

    with open("experiment_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"✅ 结果已保存到 experiment_results.json")
    print("=" * 70)

    return results

if __name__ == "__main__":
    asyncio.run(run_experiment())
