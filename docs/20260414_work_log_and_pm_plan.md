# 🏛️ SpineDoc 开发阶段报告：2026/04/14 AM

## 1. 上午总结：逻辑涌现与数据主权 (Completed)

### 1.1 核心架构：RAG 3.5 "Operation Emergent Spine"
- **突破性进度**：实现了在没有任何原始目录的情况下，通过“原子切片 -> 局部共识 -> 主权章节”的自下而上蒸馏算法（Negative Levels -1 to -3），自动构建逻辑脊梁。
- **Schema 统一**：在 `TocItem` 与 `SpineNode` 中成功注入 `is_synthetic` 字段，实现了原生目录与合成逻辑在同一套 API 契约下的和谐共存。
- **主权判定**：重构了 `SpineEngine.ingest_document` 的判定优先级。除非有显式人工引导，否则一律强制执行逻辑涌现，彻底消灭了“低质元数据”带来的干扰。

### 1.2 危机处理：数据复兴 (Operation Phoenix)
- **事件**：鲁莽的测试脚本触发了数据库 TRUNCATE。
- **补救**：利用 SpineDoc 的 **OCR 缓存主权机制**，通过 `.ocr_cache.json` 和 `.toc_spine.json` 在 60 秒内完美恢复了 406 页长文档的所有脊梁与切片数据。
- **教训**：彻底切除了代码库中的 `nuke_database` 危险方法，建立了“只增不删”的实验室纪律。

---

## 2. 下午展望：单文档证人与联邦质证 (Next Steps)

### 2.1 核心目标：构建 "WitnessNode" (证人节点)
- **哲学**：单文档 Agent 必须扮演“诚实的证人”，其证词必须 100% 忠于原文，严禁使用任何外部先验知识。
- **任务拆解**：
    1. **Scout (侦察任务)**：实现基于主问题的启发式子问题拆解（如：番茄炒蛋模型）。
    2. **Witness (物理收割)**：利用 3.0 金字塔检索器并发收割指纹池。
    3. **Examiner (逻辑质证)**：实现“质证员” Agent，通过审视 TOC 逻辑图和指纹，剔除向量检索产生的“语义漂移”。
    4. **Deposition (产出证词)**：生成包含物理证据链（Page/ID）的结构化单文档回答。

### 2.2 关键纪律
- **解耦单/多文档**：下午的任务仅聚焦于单文档证词的纯净度，为晚些时候的“多文档联邦辩论”打下地基。
- **性能与成本控制**：质证阶段仅传输元数据（Tags/Path），严禁全量传输正文，保持系统的“刺客级”敏捷。

---

## 3. 下午战略规划：联邦质证与知识主权 (Strategic Roadmap)

### 3.1 核心任务：实现 "WitnessNode" 3.5
- **意图拆解 (Query Decomposition)**：实现“侦察员”逻辑。将主问题拆解为 3 个互补的子问题，彻底解决语义稀疏性导致的漏检问题。
- **逻辑质证 (Cross-Examination)**：引入质证 Agent。不再盲目相信向量相似度，利用 TOC 脊梁与 KeyBERT 指纹对收割结果进行“去噪”和“纠偏”。
- **物理溯源 (Physical Traceability)**：强制 LLM 在返回证词时提供 `citation_ids` 列表。确保答案中的每一句话都能物理回溯到数据库中的特定 Chunk ID。

### 3.2 架构愿景：从 RAG 转向 LLM Wiki (Karpathy Style)
- **知识迭代接口**：在 `backend` 层预留切片的增删改查 (CRUD) 接口。允许未来的“联邦法官”根据最新证据修正旧的切片内容，实现知识的“自愈”与“复利”。
- **双轨主权模式**：
    - **Forensic Mode (法医模式)**：100% 忠于本地 ISR，严禁调用 LLM 训练知识。
    - **Research Mode (研究模式)**：允许调用外部联网信息（Scout 变体），但必须通过 `source` 字段进行物理隔离。

### 3.3 关键纪律 (The Code of Conduct)
- **指纹质证，不传全文**：为了极致的性能与成本控制，质证员 Agent 仅审视元数据。
- **数据契约钢性化**：证人节点的输出必须符合标准的 `Testimony` JSON 契约。

---
**Architect:** Robert C. Martin (Uncle Bob) & Andrej Karpathy
**Status:** PM Strategy Locked. Initialization...
