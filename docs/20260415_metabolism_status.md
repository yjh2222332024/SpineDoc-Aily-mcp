# 🏛️ SpineDoc 架构演进与知识主权宪法 (2026-04-15)

## 1. 核心哲学：知识主权与 Git 溯源
SpineDoc 坚持 **“文档证人优先 (Document-Witness First)”** 的核心准则。我们认为本地 ingestion 的文档是知识的“主权边界”。外部网络见证人 (Internet Witnesses) 仅能作为“参考补丁 (Git PR)”，绝不能直接篡改本地主权。

## 2. 系统演进报告

### 🏗️ V4.1 核心架构升级 (已完成)
*   **多锚点投影 (Multi-Anchor Projection)**：
    *   **旧制**：单星系映射，导致严重的“语义碎片化”与“Limbo 阻塞”。
    *   **新制**：引入 N:N 映射逻辑。文档根据前 3 位高权重关键词同时投影至多个星系，如一篇“农业 RAG”论文同时归属于 `Galaxy_Agriculture` 与 `Galaxy_RAG`。
*   **星系引力净化**：
    *   实现了 **“零容忍”噪声过滤器**。在 `KeywordExtractor` 层级，对包含“参考文献”、“附录”等 Boilerplate 词汇的 2-gram 关键词进行物理剔除，彻底解决了星系名称被噪音污染的问题。
*   **物理层确权**：
    *   成功部署 `Galaxy`、`DocumentGalaxyLink` 与 `ChunkRevision` 表，并在 PostgreSQL 中物理生效。通过 `init_db` 实现了非破坏性的增量架构同步。

### 🧠 规划中的代谢代谢与 Git 溯源协议 (进行中)
*   **四色置信度映射 (The 4-Color Confidence Matrix)**：
    *   🟢 **绿色 (Verified)**：文档证人与权威学术网络高度一致。
    *   🟡 **黄色 (Conflict)**：权威网络与文档冲突，触发法庭辩论 (Federated Debate)。
    *   🟠 **橙色 (Ambiguous)**：网络见证人与文档存在差异，但来源置信度一般。
    *   🔴 **红色 (Untrusted)**：仅有“野鸡网站”反驳本地文档，置信度直接被系统拒绝入库。
*   **Git 代谢账本 (`ChunkRevision`)**：
    *   所有知识修正不执行 `DELETE/UPDATE`，而是通过记录 `old_content`、`new_content`、`change_reason` 和 `contributor_agent` 实现不可变账本。

## 3. 预期达成的工程效果
1.  **自动归类稳定性**：不再产生大量成员数为 1 的“孤岛星系”，而是让文档在 3-5 个核心领域星系内实现多向汇聚，极大提升检索召回率。
2.  **知识库呼吸率**：系统将具备实时识别陈旧知识的能力。随着 `Internet Witness` 的增量接入，`ChunkRevision` 会记录下每一次知识纠偏，实现像 Git 一样的知识库演进记录。
3.  **防污染架构**：通过锚点星系名称净化，知识库的导航结构将变得异常简洁，用户能一眼看出系统关注的逻辑主权领域。

---
*“我们不只是在写程序，我们是在赋予系统判断真理的权利。”*
*架构审计员：SpineDoc System Agent*
