# 🏛️ SpineDoc (阅脊) - Project Mandates & Architecture Guide

## 🌟 Project Overview
**SpineDoc** is an advanced Structural RAG (Retrieval-Augmented Generation) engine designed for high-precision logic auditing of long and complex documents. It moves beyond simple text-chunking by reconstructing the **Implicit Spine (ISR)** of documents and employing a **Federated Debate** mechanism for forensic reasoning and fact-checking.

### 🔱 Trident Architecture
1.  **Engine Layer (CLI)**: The "Logic Assassin" terminal for bulk document ingestion and multi-agent debate.
2.  **Protocol Layer (MCP)**: Native Model Context Protocol server for integration with IDEs (Claude Desktop, Cursor).
3.  **Intelligence Layer (Agents)**: A LangGraph-powered fleet of agents (Distributor, Witness, Moderator, Integrator) that perform page-level forensic analysis.

---

## 🏗️ Technical Stack
- **Language**: Python 3.12+
- **Backend**: FastAPI, SQLModel (SQLAlchemy + Pydantic), PostgreSQL with `pgvector`.
- **CLI**: Typer, Rich (for terminal UI/UX).
- **PDF/NLP**: PyMuPDF (`fitz`), `jieba` (Chinese segmentation).
- **AI/LLM**: LangGraph (Agent orchestration), OpenAI/DeepSeek API, SiliconFlow (Embeddings).
- **Storage**: Asyncpg, Redis (Caching/Status).

---

## 🛠️ Building and Running

### 1. Environment Setup
- Copy `.env.template` to `.env`.
- **Required Keys**: `DATABASE_URL`, `OPENAI_API_KEY`, `EMBEDDING_API_KEY` (SiliconFlow recommended).
- **Database**: Requires PostgreSQL with the `vector` extension.

### 2. Installation
```bash
# Install in editable mode
pip install -e .
```

### 3. Key Commands
| Command | Description |
| :--- | :--- |
| `spine ingest <path>` | Extract ISR, perform OCR, and vectorize document segments. |
| `spine ask "<query>"` | Initiate Federated Debate for high-precision forensic answers. |
| `spine list` | View all indexed documents in the "Knowledge Galaxy". |
| `spine chunks <id>` | Inspect semantic slices and keywords for a specific document. |
| `uvicorn backend.app.main:app` | Start the FastAPI backend server. |

### 4. Testing
- Run all tests: `pytest backend/tests`
- Atomic verification: `python tests/atomic_runner.py`
- End-to-end audit: `python backend/scripts/final_grand_audit.py`

---

## 🛡️ 架构安全与变更纪律 (Mandatory Safety Protocols)

为了保护 SpineDoc 的核心逻辑稳定性，所有涉及架构变更的操作必须严格遵循以下纪律：

1.  **强制备份 (Physical Backup)**：任何涉及删除或重构现有核心代码（特别是 `federated_court`, `navigator`, `splitter` 等模块）的操作，必须在执行删除前将原代码备份至 `backups/` 目录下，并以时间戳命名。
2.  **强制日志 (Change Log)**：所有重大逻辑变更必须同步更新至 `docs/20260409_dev_log.md`，记录变更背景、修改内容、性能影响及验证状态。
3.  **变更审核 (Pre-Approval)**：严禁在未经过你明确确认的情况下物理删除或弃用任何核心架构路径。优化或“ deprecation ”需先以文字形式提交方案，经确认后方可执行。
4.  **死线 (Dead-lines)**：
    -   凡是涉及逻辑移除，必留 `compatibility_layer`（兼容层）或注释说明，禁止直接 `rm` 文件。
    -   若发现未记录变更即修改核心架构，系统视为“非专业操作”。

---

## 📂 Key Directory Structure
- `spine_cli/`: Core terminal application and agent prompts.
- `backend/app/`: FastAPI backend (API endpoints, services, models).
- `backend/spine.py`: The core `SpineCore` engine bridge.
- `docs/`: Technical documentation (Architecture, Benchmarks).
- `scripts/`: Diagnostic, migration, and benchmarking tools.
- `evaluation/`: SOTA pressure tests and metric evaluation datasets.

---

## 🗺️ 2026 Roadmap Highlights
- **Engine Fusion**: Integrating `Navigator`'s deep-water retrieval into `Federated Witness`.
- **Knowledge Metabolism**: Automated patching/pruning of stale knowledge based on court verdicts.
- **Visual Dashboard**: Real-time 4-color confidence highlighting in a React frontend.
