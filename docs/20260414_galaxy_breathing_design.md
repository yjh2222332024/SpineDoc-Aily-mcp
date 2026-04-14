# 🏛️ SpineDoc 架构演进：知识星系 (Operation Galaxy Breath)

**Date**: 2026-04-14 PM
**Architect**: Karpathy & Uncle Bob
**Status**: Design Locked / Implementation Starting

## 1. 哲学背景：Software 3.0 的语义引力
传统的私有知识库 (RAG) 往往受困于“文件夹”或“单维度标签”的思维定式。这种“番茄炒蛋”悖论——即一个事实单元可能同时属于多个领域——导致了检索时的语义漂移。

**Operation Galaxy Breath** 的核心思想是将文档视为语义空间中的实体，它们不属于星系，而是受到星系的“引力捕获”。

## 2. 核心架构：多中心流形 (Multi-centric Manifold)

### 2.1 Galaxy (星系层)
星系不再是物理容器，而是**语义重心 (Centroid)**。
- 每个星系有一个由核心文档簇蒸馏出的 `centroid_embedding`。
- 星系拥有一个 `description`，定义了该领域的逻辑边界。

### 2.2 GalaxyLink (引力链接层)
这是实现“呼吸”的关键。
- **N:N 映射**：一个 `Document` 可以被多个 `Galaxy` 捕获。
- **Relevance Weight (关联权重)**：记录文档在不同星系中的引力大小。
- **Perspective Summary (视角摘要)**：同一份文档，在 [AI 星系] 和 [烹饪星系] 的视角下，其元数据摘要是完全不同的。

## 3. 逻辑流：引力撞击 (Gravitational Impact)

1.  **Galaxy Scouting**: 原始问题首先与所有 `Galaxy` 的重心进行向量碰撞，锁定 Top-N 星系。
2.  **Contextual Routing**: 系统根据锁定的星系，通过 `DocumentGalaxyLink` 筛选出高关联文档。
3.  **Witness Dispatch**: 为每个关联文档分配一个 `WitnessNode`（单文档 Agent）。
4.  **Federated Consensus**: 大法官汇总各星系的证词，进行跨星系的逻辑质证。

## 4. 知识代谢 (Knowledge Metabolism)
- **自愈 (Self-healing)**：当新的高置信度证据出现时，通过 CRUD 修改 Chunk 的 `veracity_score`。
- **迁移 (Migration)**：随着知识演化，文档在星系间的 `relevance_score` 会动态更新。

## 5. 待办事项 (Next Steps)
- [ ] 在 `backend/app/core/models.py` 中新增 `Galaxy` 和 `DocumentGalaxyLink` 模型。
- [ ] 实现 `GalaxyDiscoverer`：自动聚类存量文档。
- [ ] 升级 `SpineEngine.hybrid_ask`：支持“星系 -> 文档 -> 证人”的级联调度。

---
**"Vibe Coding: Design with Empathy, Execute with Precision."**
