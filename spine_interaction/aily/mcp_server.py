"""
 SpineDoc MCP Server - AI 逻辑质证协议接口
===========================================
职责：提供符合 Model Context Protocol (MCP) 标准的工具集，供 AI 代理直接调用。
架构：属于 Interaction Layer，作为 LLM 与 Backend Engine 之间的标准化桥梁。
"""

import asyncio
import hashlib
import os
import sys
import json
from pathlib import Path
from typing import Optional, Any

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
import anyio
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.spine_engine import SpineEngine
from backend.app.services.spine_agent import SpineAgent
from backend.app.infra.lark_cli_reporter import LarkCliReporter
from backend.app.infra.memory.amem_adapter import AmemAdapter
from backend.app.services.feishu.bitable_ledger import bitable_ledger
from backend.app.services.ingestion.embedding import embedding_service
from backend.app.services.feishu.file_resolver import FileResolver
from backend.app.services.knowledge.git_manager import get_git_manager
from backend.app.services.ingestion.zhipu_reranker import zhipu_reranker

import logging

# ── SpineAgent Singleton ──────────────────────────────────────
_agent: Optional[SpineAgent] = None
_agent_lock = asyncio.Lock()

async def get_agent() -> SpineAgent:
    """Return a singleton SpineAgent, creating it on first call."""
    global _agent
    if _agent is None:
        async with _agent_lock:
            if _agent is None:
                _agent = SpineAgent(
                    memory=AmemAdapter(),
                    reporter=LarkCliReporter(),
                    store=bitable_ledger,
                )
    return _agent


# 文档搜索缓存：key=doc_id, value={"text": str, "vector": ndarray}
# 首次搜索后缓存文档向量，后续搜索跳过 embedding 已缓存的文档
_doc_search_cache: dict = {}

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("spinedoc_mcp")


class TimeoutFastMCP(FastMCP):
    """带超时保护的 FastMCP，所有 tool 调用超过 timeout 自动取消。"""

    def __init__(self, *args, tool_timeout: float = 300.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.tool_timeout = tool_timeout

    async def call_tool(self, name: str, arguments: dict) -> Any:
        context = self.get_context()
        logger.info(f"[TimeoutFastMCP] 执行 tool={name}, timeout={self.tool_timeout}s")
        try:
            with anyio.fail_after(self.tool_timeout):
                return await self._tool_manager.call_tool(
                    name, arguments, context=context, convert_result=True
                )
        except TimeoutError:
            logger.warning(f"[TimeoutFastMCP] Tool '{name}' 超时 ({self.tool_timeout}s)")
            raise ToolError(f"Tool '{name}' timed out after {self.tool_timeout}s")
        except anyio.get_cancelled_exc_class():
            logger.warning(f"[TimeoutFastMCP] Tool '{name}' 被客户端取消")
            raise


mcp = TimeoutFastMCP(
    "spinedoc_mcp",
    tool_timeout=300.0,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "127.0.0.1:*", "localhost:*", "[::1]:*",
            "spinedoc.xiangyinben.xyz",
            "spinedoc.xiangyinben.xyz:*",
        ],
        allowed_origins=[
            "http://127.0.0.1:*", "http://localhost:*", "http://[::1]:*",
            "https://spinedoc.xiangyinben.xyz",
            "https://spinedoc.xiangyinben.xyz:*",
        ],
    ),
)


# ─────────────────────────────────────────────────
#  工具 1: 导入文档
# ─────────────────────────────────────────────────

@mcp.tool()
async def spinedoc_ingest(
    file_path_or_token: str,
    toc_range: Optional[str] = None,
) -> str:
    """
    将文档导入到 SpineDoc 知识库。
    """
    import re
    logger.info(f" [MCP] 开始处理输入: {file_path_or_token[:50]}...")

    try:
        resolver = FileResolver()
        # 解析 token 或路径
        resolved_path = await resolver.resolve(file_path_or_token)

        # 解析 toc_range 为列表
        manual_toc_range = None
        if toc_range:
            nums = [int(n) for n in re.findall(r'\d+', str(toc_range))]
            if len(nums) >= 1:
                manual_toc_range = list(range(min(nums), max(nums) + 1))
                logger.info(f" [MCP] 解析目录范围: P{min(nums)}-P{max(nums)}")

        reporter = LarkCliReporter()
        memory = AmemAdapter()
        engine = SpineEngine(reporter=reporter, memory=memory)

        ingest_res = await engine.ingest_document(
            resolved_path,
            manual_toc_range=manual_toc_range
        )

        doc_id = ingest_res.get("id", "")
        filename = ingest_res.get("filename", Path(resolved_path).name)
        status = ingest_res.get("status", "unknown")

        result = {
            "doc_id": doc_id,
            "filename": filename,
            "status": status,
            "chunk_count": ingest_res.get("chunk_count", 0),
        }
        logger.info(f" [MCP] 导入完成: {filename} -> {doc_id[:16]}...")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f" [MCP] 导入失败: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


# ─────────────────────────────────────────────────
#  [NEW] 工具 2: 质证规划 (Plan)
# ─────────────────────────────────────────────────

@mcp.tool()
async def spinedoc_plan(query: str, doc_id: str = "all") -> str:
    """
    对用户查询进行逻辑拆解，制定质证计划。
    这是逻辑质证的第一步。
    """
    logger.info(f" [MCP] 正在制定质证计划: {query[:40]}...")
    try:
        agent = await get_agent()
        agent.reset(query, doc_id=doc_id)
        plan = await agent.plan()

        return json.dumps({
            "query": query,
            "sub_queries": plan.get("sub_queries", []),
            "focus_areas": plan.get("focus_areas", []),
            "next_step": "spinedoc_collect"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ─────────────────────────────────────────────────
#  [NEW] 工具 3: 证据收割 (Collect)
# ─────────────────────────────────────────────────

@mcp.tool()
async def spinedoc_collect(query: str, sub_queries: list[str], doc_id: str = "all") -> str:
    """
    根据质证计划，从本地星系和互联网证人处收割证据片。
    这是逻辑质证的第二步。使用并发子智能体并行召回。
    """
    logger.info(f" [MCP] 正在收割证据: {len(sub_queries)} 个子查询")
    try:
        agent = await get_agent()
        # Sync sub_queries from previous plan step into agent state
        agent._state["sub_queries"] = sub_queries
        agent._state["doc_id"] = doc_id

        harvest_result = await agent.harvest()
        pool = agent.get_evidence_pool()

        return json.dumps({
            "evidence_count": len(pool),
            "evidence_samples": [e.get("content", "")[:100] for e in pool[:3]],
            "evidence_ids": [e.get("id") for e in pool],
            "next_step": "spinedoc_audit"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ─────────────────────────────────────────────────
#  [NEW] 工具 4: 逻辑审计 (Audit)
# ─────────────────────────────────────────────────

@mcp.tool()
async def spinedoc_audit(query: str, evidence_ids: list[str], evidence_pool_json: str = "",
                         doc_id: str = "all") -> str:
    """
    对已收割的证据片执行逻辑审计，检测冲突并进行贝叶斯评分。
    这是逻辑质证的第三步。
    如果从 spinedoc_collect 获得了 evidence_pool_json，传入它以保留完整的证据元数据。
    """
    logger.info(f" [MCP] 正在审计证据: {len(evidence_ids)} 条, pool_json={'有' if evidence_pool_json else '无'}")
    try:
        agent = await get_agent()

        # Backward compat: if evidence_pool_json provided, merge into agent state
        if evidence_pool_json:
            try:
                evidence_pool = json.loads(evidence_pool_json)
                agent._state["evidence_pool"] = evidence_pool
                logger.info(f" [MCP] 使用完整证据池 ({len(evidence_pool)} 条，含元数据)")
            except json.JSONDecodeError:
                logger.warning(" [MCP] evidence_pool_json 解析失败，使用 agent 内部状态")

        audit_res = await agent.audit()

        return json.dumps({
            "conflicts": audit_res.get("conflicts", []),
            "weights": audit_res.get("claim_weights", {}),
            "evidence_pool": audit_res.get("evidence_pool", []),
            "next_step": "spinedoc_summarize"
        }, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ─────────────────────────────────────────────────
#  [NEW] 工具 4.5: 人工仲裁 RED 冲突（默认路径）
# ─────────────────────────────────────────────────

@mcp.tool()
async def spinedoc_arbitrate_conflict(
    query: str,
    evidence_ids: list[str],
    conflict_id: str,
    resolution: str,
    human_notes: str = "",
    weights_json: str = "",
    conflicts_json: str = "",
) -> str:
    """
    【默认路径】人工仲裁 RED 冲突：当 AI 无法判断冲突胜负时，由人类做出最终裁定。
    调用后自动进入判决阶段，返回判决书。

    Args:
        query: 原始查询
        evidence_ids: 证据 ID 列表（审计阶段使用的，用于从 bitable 恢复原文）
        conflict_id: 要仲裁的冲突描述（从 spinedoc_audit 结果的 conflicts 数组取 description 字段）
        resolution: accept_a（采纳证据A）| accept_b（采纳证据B）| reject_both（双方驳回）| merge（双方合并）
        human_notes: 人类判断的依据说明
        weights_json: 审计阶段的 claim_weights JSON
        conflicts_json: 审计阶段的 conflicts JSON
    """
    logger.info(f" [MCP] 收到人工仲裁: conflict={conflict_id}, resolution={resolution}")

    try:
        # 1. 恢复证据池（同 spinedoc_summarize 模式）
        evidence_pool = []
        recv_ids = [eid for eid in evidence_ids if eid.startswith("rec")]
        if recv_ids:
            async def _fetch(rid):
                return await bitable_ledger.get_chunk(rid)
            tasks = [_fetch(rid) for rid in recv_ids]
            fetched = [f for f in await asyncio.gather(*tasks) if f]
            evidence_pool = fetched

        # 2. 重建 audited_data
        weights = json.loads(weights_json) if weights_json else {}
        conflicts = json.loads(conflicts_json) if conflicts_json else []

        audited_data = {
            "evidence_pool": evidence_pool,
            "conflicts": conflicts,
            "claim_weights": weights,
        }

        # 3. 执行仲裁
        memory = AmemAdapter()
        engine = SpineEngine(memory=memory)
        verdict = await engine.arbitrate_conflict(
            query=query,
            audited_data=audited_data,
            conflict_id=conflict_id,
            resolution=resolution,
            human_notes=human_notes,
        )

        if "error" in verdict:
            return json.dumps(verdict, ensure_ascii=False)

        # 4. 补充 evolution_proposal 的 old_content
        git_mgr = get_git_manager()
        for item in verdict.get("evolution_proposal", []):
            chunk_id = item.get("chunk_id")
            if chunk_id:
                old = git_mgr.get_chunk_at_commit(chunk_id, "HEAD")
                item["old_content"] = (old or {}).get("content", "")
            else:
                item["old_content"] = ""

        # 5. 附上证据池
        verdict["evidence_pool"] = evidence_pool

        return json.dumps(verdict, ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f" [MCP] 仲裁失败: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg}, ensure_ascii=False)


# ─────────────────────────────────────────────────
#  [NEW] 工具 4.6: 自动解决 RED 冲突（懒人可选路径）
# ─────────────────────────────────────────────────

@mcp.tool()
async def spinedoc_auto_resolve_conflicts(
    query: str,
    evidence_ids: list[str],
    doc_id: str = "all",
    weights_json: str = "",
    conflicts_json: str = "",
) -> str:
    """
    【可选路径】自动解决 RED 冲突：当人类懒得逐条裁定时，AI 执行重审计+强制贝叶斯决断。
    人懒时用，效率优先。

    Args:
        query: 原始查询
        evidence_ids: 证据 ID 列表
        doc_id: 文档范围（默认 "all" 表示全库）
        weights_json: 审计阶段的 claim_weights JSON
        conflicts_json: 审计阶段的 conflicts JSON
    """
    logger.info(f" [MCP] 自动解决冲突: {len(evidence_ids)} 条证据")

    try:
        # 1. 恢复证据池
        evidence_pool = []
        recv_ids = [eid for eid in evidence_ids if eid.startswith("rec")]
        if recv_ids:
            async def _fetch(rid):
                return await bitable_ledger.get_chunk(rid)
            tasks = [_fetch(rid) for rid in recv_ids]
            fetched = [f for f in await asyncio.gather(*tasks) if f]
            evidence_pool = fetched

        weights = json.loads(weights_json) if weights_json else {}
        conflicts = json.loads(conflicts_json) if conflicts_json else []

        # 2. 用现有证据重跑审计
        memory = AmemAdapter()
        engine = SpineEngine(memory=memory)
        audit_res = await engine.audit_evidence(
            query=query,
            evidence_ids=evidence_ids,
            evidence_pool=[e for e in evidence_pool if e.get("id") in evidence_ids],
            doc_id=doc_id,
        )

        # 3. 仍有不确定冲突？用 BayesianAggregator 强制决断
        remaining = audit_res.get("conflicts", [])
        if remaining:
            weights = audit_res.get("claim_weights", {})
            for c in remaining:
                packages = c.get("packages", [])
                ev_ids = [p["chunk_id"] for p in packages if "chunk_id" in p]
                ev_a = ev_ids[0] if len(ev_ids) > 0 else None
                ev_b = ev_ids[1] if len(ev_ids) > 1 else None
                if ev_a and ev_b and ev_a in weights and ev_b in weights:
                    total = weights[ev_a] + weights[ev_b]
                    if total > 0:
                        weights[ev_a] = weights[ev_a] / total
                        weights[ev_b] = weights[ev_b] / total

        # 4. 走 synthesize
        verdict = await engine.synthesize_verdict(query, {
            "evidence_pool": evidence_pool,
            "conflicts": remaining,
            "claim_weights": weights,
            "auto_resolved": True,
        })

        # 5. 补充证据原文
        verdict["evidence_pool"] = evidence_pool
        return json.dumps(verdict, ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f" [MCP] 自动解决失败: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg}, ensure_ascii=False)


# ─────────────────────────────────────────────────

@mcp.tool()
async def spinedoc_summarize(query: str, evidence_ids: list[str],
                              weights_json: str = "", conflicts_json: str = "",
                              doc_id: str = "all") -> str:
    """
    根据审计后的证据和冲突裁决，给出最终的逻辑判决书。
    这是逻辑质证的最后一步。

    Args:
        query: 原始查询问题
        evidence_ids: 审计阶段使用的证据 ID 列表（用于从 bitable 恢复原文）
        weights_json: 贝叶斯权重 JSON，key=evidence_id, value=权重分数
        conflicts_json: 冲突列表 JSON
        doc_id: 文档范围（默认 "all" 表示全库）
    """
    logger.info(f" [MCP] 正在生成判决书, evidence_ids={len(evidence_ids)}")
    try:
        agent = await get_agent()

        # Backward compat: merge weights/conflicts from MCP params into agent state
        if weights_json:
            try:
                agent._state["claim_weights"] = json.loads(weights_json)
            except json.JSONDecodeError:
                pass
        if conflicts_json:
            try:
                agent._state["conflicts"] = json.loads(conflicts_json)
            except json.JSONDecodeError:
                pass

        # Synthesize
        synth_res = await agent.synthesize()
        verdict = agent._export_result()

        # Add evolution_proposal with old_content for diff cards
        git_mgr = get_git_manager()
        evolution_proposal = []
        for chunk in agent.get_evidence_pool():
            if chunk.get("origin") != "TEMP":
                item = {
                    "chunk_id": chunk.get("id", ""),
                    "content": chunk.get("content", ""),
                    "logic_tags": chunk.get("claims", []),
                    "document_id": chunk.get("doc_id", ""),
                }
                chunk_id = item["chunk_id"]
                if chunk_id:
                    old = git_mgr.get_chunk_at_commit(chunk_id, "HEAD")
                    item["old_content"] = (old or {}).get("content", "")
                else:
                    item["old_content"] = ""
                evolution_proposal.append(item)

        verdict["evolution_proposal"] = evolution_proposal

        # Attach evidence pool with original content
        evidence_pool = agent.get_evidence_pool()
        verdict["evidence_pool"] = evidence_pool

        # Fetch original content for evidence items
        if evidence_pool:
            doc_to_evidence = {}
            for e in evidence_pool:
                eid = e.get("doc_id")
                if eid:
                    doc_to_evidence.setdefault(eid, []).append(e["id"])

            async def _fetch_by_doc(did):
                chunks = await bitable_ledger.fetch_chunks_by_document(did, limit=200)
                return {c["id"]: c["content"] for c in chunks}

            if doc_to_evidence:
                tasks = [_fetch_by_doc(did) for did in doc_to_evidence]
                results = await asyncio.gather(*tasks)
                chunk_map = {}
                for r in results:
                    chunk_map.update(r)
                for e in evidence_pool:
                    e["original_content"] = chunk_map.get(e["id"], "")

            unmatched = [e for e in evidence_pool
                         if not e.get("original_content") and e["id"].startswith("rec")]
            if unmatched:
                async def _fetch_single(e_):
                    chunk = await bitable_ledger.get_chunk(e_["id"])
                    return (e_["id"], chunk["content"]) if chunk else (e_["id"], "")
                single_results = await asyncio.gather(*[_fetch_single(e) for e in unmatched])
                single_map = dict(single_results)
                for e in evidence_pool:
                    if not e.get("original_content"):
                        e["original_content"] = single_map.get(e["id"], "")

        return json.dumps(verdict, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ─────────────────────────────────────────────────
#  工具 5.5: 一键质证 (Single-Agent Full Pipeline)
# ─────────────────────────────────────────────────

@mcp.tool()
async def spinedoc_run(query: str, doc_id: str = "all") -> str:
    """
    一键执行完整逻辑质证流程（PLAN→HARVEST→AUDIT→SYNTHESIZE）。
    使用单智能体 + 并发子智能体召回，无需分步调用。
    """
    logger.info(f" [MCP] 一键质证: {query[:40]}...")
    try:
        agent = await get_agent()
        result = await agent.run_full(query, doc_id=doc_id)

        # Attach evolution_proposal
        git_mgr = get_git_manager()
        evolution_proposal = []
        for chunk in agent.get_evidence_pool():
            if chunk.get("origin") != "TEMP":
                item = {
                    "chunk_id": chunk.get("id", ""),
                    "content": chunk.get("content", ""),
                    "logic_tags": chunk.get("claims", []),
                    "document_id": chunk.get("doc_id", ""),
                }
                chunk_id = item["chunk_id"]
                if chunk_id:
                    old = git_mgr.get_chunk_at_commit(chunk_id, "HEAD")
                    item["old_content"] = (old or {}).get("content", "")
                else:
                    item["old_content"] = ""
                evolution_proposal.append(item)

        result["evolution_proposal"] = evolution_proposal
        result["evidence_pool"] = agent.get_evidence_pool()
        result["phase_log"] = agent.get_phase_log()

        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ─────────────────────────────────────────────────
#  工具 6: 演化核准 (Sovereign Evolution)
# ─────────────────────────────────────────────────

@mcp.tool()
async def spinedoc_approve_evolution(proposal_json: str) -> str:
    """
    核准并执行知识库演化。
    proposal_json 是从 spinedoc_summarize 结果中获取的 evolution_proposal。
    只有当用户明确核准后，这些新发现的逻辑规律才会进入主权记忆库。
    """
    logger.info(" [MCP] 收到演化核准指令，正在写入主权记忆...")

    try:
        proposal = json.loads(proposal_json)
        memory = AmemAdapter()

        # 指纹去重：跳过逻辑指纹已存在的项
        count = 0
        for item in proposal:
            fingerprint = hashlib.md5(item.get("content", "").encode()).hexdigest()
            existing = await bitable_ledger.find_by_fingerprint(fingerprint)
            if existing:
                logger.info(f" [MCP] 跳过重复: {fingerprint[:8]}")
                continue
            await memory.ingest_memory(item)
            count += 1

        # Git 同步：核准的知识写入版本仓库
        git_mgr = get_git_manager()
        git_chunks = [
            {"chunk_id": item["chunk_id"], "content": item["content"]}
            for item in proposal if item.get("chunk_id")
        ]
        if git_chunks:
            git_mgr.commit_chunks_batch(git_chunks, message=f"主权演化核准: {count} 条")

        logger.info(f" [MCP] 演化执行完成，新增 {count} 条逻辑记忆")
        return json.dumps({"status": "success", "added_count": count}, ensure_ascii=False)

    except Exception as e:
        error_msg = f" [MCP] 演化执行失败: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


# ─────────────────────────────────────────────────
#  工具 7: 列出已导入文档
# ─────────────────────────────────────────────────

@mcp.tool()
async def spinedoc_list_docs() -> str:
    """
    列出知识库中所有已导入的文档及其基本信息。
    """
    logger.info("📋 [MCP] 列出所有文档")

    try:
        docs = await bitable_ledger.list_documents()
        return json.dumps({
            "documents": docs,
            "total": len(docs),
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f" [MCP] 列出文档失败: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


@mcp.tool()
async def spinedoc_find_docs(description: str, limit: int = 5,
                              use_reranker: bool = False) -> str:
    """
    通过自然语言描述，语义搜索已导入的文档。
    适用于用户不记得文档 ID 或精确文件名时。

    Args:
        description: 自然语言描述（如"关于违约金的合同"）
        limit: 返回结果数
        use_reranker: 是否启用智谱 rerank 对 top-5 深度重排（更高精度，+~0.5s）
    """
    logger.info(f"  [MCP] 语义搜索文档: {description[:40]}...")
    try:
        docs = await bitable_ledger.list_documents()
        if not docs:
            return json.dumps({"documents": [], "total": 0}, ensure_ascii=False)

        # Phase 1: 一次搜索拉取所有文档的 chunks，按 doc 内存分组
        # 避免 55 次独立 API 调用（每次 3-5s 太慢）
        logger.info(f"  [MCP] 批量拉取所有文档的 chunks...")
        chunks_table = bitable_ledger.tables['chunks']['id']
        search_url = (
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/"
            f"{bitable_ledger.app_token}/tables/{chunks_table}/records/search"
        )
        resp = await bitable_ledger._api_request(
            "POST", search_url,
            json_data={"page_size": 500}
        )
        items = resp.get("data", {}).get("items", [])

        # 按 doc_record_id 分组
        doc_chunks_map: dict = {}
        for it in items:
            f = it.get("fields", {})
            # Bitable 关联字段格式: [{"text": "recxxx", "type": "text"}]
            doc_id = bitable_ledger._plain_text(f.get("文档关联", ""))
            if not doc_id:
                continue
            chunk = {
                "id": it["record_id"],
                "summary": bitable_ledger._plain_text(f.get("逻辑摘要", "")),
                "content": bitable_ledger._plain_text(f.get("正文内容", "")),
                "logic_tags": f.get("语义标签", []),
                "breadcrumb": bitable_ledger._plain_text(f.get("逻辑面包屑", "")),
            }
            doc_chunks_map.setdefault(doc_id, []).append(chunk)

        # 排序确保一致性：取每组前 2 个
        all_chunks = []
        for doc in docs:
            chunks = doc_chunks_map.get(doc["id"], [])[:2]
            all_chunks.append(chunks)

        # 构建富文本: "filename | chunk1.逻辑摘要 | chunk1.正文前200字 | chunk2.语义标签"
        doc_texts = []
        for i, doc in enumerate(docs):
            parts = [doc.get("filename", "")]
            for c in all_chunks[i]:
                summary = c.get("summary", "")
                content = c.get("content", "")[:200]
                tags = bitable_ledger._plain_text(c.get("logic_tags", ""))
                breadcrumb = c.get("breadcrumb", "")
                parts.extend([s for s in [summary, content, tags, breadcrumb] if s])
            doc_texts.append(" | ".join(parts))

        # Phase 2: 向量化 + 缓存
        global _doc_search_cache
        doc_vectors = np.zeros((len(docs), 0))
        need_embed = []

        for i, doc in enumerate(docs):
            cached = _doc_search_cache.get(doc["id"])
            if cached is not None:
                # 检查富文本是否一致（防止文档内容变更导致缓存脏）
                if cached["text"] == doc_texts[i]:
                    if doc_vectors.shape[1] == 0:
                        doc_vectors = np.zeros((len(docs), len(cached["vector"])))
                    doc_vectors[i] = cached["vector"]
                    continue
            need_embed.append(i)

        if need_embed:
            texts_to_embed = [doc_texts[i] for i in need_embed] + [description]
            vectors = await embedding_service.get_embeddings(texts_to_embed)
            if not vectors or len(vectors) < 2:
                return json.dumps({"documents": [], "total": 0}, ensure_ascii=False)

            # 从返回中分离 doc 向量和 query 向量
            new_doc_vecs = np.array(vectors[:-1])
            query_vec = np.array(vectors[-1])

            # 初始化 doc_vectors 矩阵
            if doc_vectors.shape[1] == 0:
                doc_vectors = np.zeros((len(docs), len(query_vec)))

            # 填充新向量并缓存
            for j, idx in enumerate(need_embed):
                _doc_search_cache[docs[idx]["id"]] = {
                    "text": doc_texts[idx],
                    "vector": new_doc_vecs[j],
                }
                doc_vectors[idx] = new_doc_vecs[j]
        else:
            # 全部缓存命中，只需嵌入 query
            logger.info("  [MCP] 全部文档向量命中缓存")
            q_vectors = await embedding_service.get_embeddings(description)
            query_vec = np.array(q_vectors[0])

        # Phase 3: 余弦相似度排序
        norms = np.linalg.norm(doc_vectors, axis=1) * np.linalg.norm(query_vec)
        norms[norms == 0] = 1e-10
        similarities = np.dot(doc_vectors, query_vec) / norms
        top_idx = np.argsort(similarities)[::-1]

        # Phase 4: 可选 rerank
        if use_reranker and len(top_idx) >= 1:
            rerank_limit = min(5, len(top_idx))
            top_k_texts = [doc_texts[top_idx[i]] for i in range(rerank_limit)]
            logger.info(f"  [MCP] 执行 rerank, {rerank_limit} 条...")
            rerank_results = await zhipu_reranker.rerank(description, top_k_texts)
            if rerank_results:
                # reranker 返回按分数降序的 results，重建排序
                rerank_scores = {}
                for item in rerank_results:
                    orig_idx = top_idx[item["index"]]
                    rerank_scores[orig_idx] = item.get("relevance_score", 0)
                # 按 rerank 分数重新排序 top_idx[:rerank_limit]
                rerank_ordered = sorted(
                    top_idx[:rerank_limit],
                    key=lambda i: rerank_scores.get(i, similarities[i]),
                    reverse=True,
                )
                top_idx = rerank_ordered + top_idx[rerank_limit:]

        # 取 top limit 条
        top_idx = top_idx[:limit]

        results = []
        for i in top_idx:
            snippets = []
            for c in all_chunks[i][:2]:
                snippet = {
                    "summary": c.get("summary", "")[:100],
                }
                snippet_content = c.get("content", "")[:150]
                if snippet_content:
                    snippet["snippet"] = snippet_content
                snippets.append(snippet)
            results.append({
                "doc_id": docs[i].get("id", ""),
                "filename": docs[i].get("filename", ""),
                "status": docs[i].get("status", ""),
                "relevance": round(float(similarities[i]), 3),
                "matched_snippets": snippets,
            })

        return json.dumps({"documents": results, "total": len(results)},
                          ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f" [MCP] 语义搜索失败: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


@mcp.tool()
async def spinedoc_trace(chunk_id: str, action: str = "history",
                         old_commit: str = "", new_commit: str = "",
                         limit: int = 20) -> str:
    """
    溯源和回滚知识块。

    Args:
        chunk_id: 知识块 ID（来自 evolution_proposal 的 chunk_id）
        action: 操作类型 history | diff | revert
        old_commit: diff 模式下的旧版本 hash，或 revert 要回滚到的版本
        new_commit: diff 模式下的新版本 hash（默认 HEAD）
        limit: history 模式下返回的版本数
    """
    from backend.app.services.knowledge.git_manager import get_git_manager
    git_mgr = get_git_manager()

    try:
        if action == "history":
            commits = git_mgr.get_chunk_history(chunk_id, limit)
            return json.dumps([{
                "hash": c.hash, "short_hash": c.short_hash,
                "message": c.message, "timestamp": str(c.timestamp),
                "author": c.author
            } for c in commits], ensure_ascii=False)

        elif action == "diff":
            new = new_commit or "HEAD"
            diff_text = git_mgr.diff_chunks(chunk_id, old_commit, new)
            return json.dumps({"chunk_id": chunk_id, "diff": diff_text},
                              ensure_ascii=False)

        elif action == "revert":
            if not old_commit:
                return json.dumps({"error": "revert 需要指定 old_commit 参数"},
                                  ensure_ascii=False)
            success = git_mgr.revert_chunk(chunk_id, old_commit)
            return json.dumps({"success": success}, ensure_ascii=False)

        else:
            return json.dumps({"error": f"未知 action: {action}"},
                              ensure_ascii=False)

    except Exception as e:
        error_msg = f" [MCP] 溯源失败: {str(e)}"
        logger.error(error_msg)
        return json.dumps({"error": error_msg}, ensure_ascii=False)


@mcp.tool()
async def spinedoc_health() -> str:
    """健康检查，返回系统状态。"""
    return json.dumps({"status": "ok", "version": "1.0"})


def main():
    """MCP server entry point with graceful shutdown."""
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    host = os.getenv("MCP_HOST", "127.0.0.1")
    port = int(os.getenv("MCP_PORT", "7000"))

    mcp.settings.host = host
    mcp.settings.port = port

    if transport == "sse":
        # Aily 需要 POST 到 /sse，使用 streamable-http 挂载到 /sse
        mcp.settings.streamable_http_path = "/sse"
        print(f"[MCP] Starting server at http://{host}:{port}/sse (POST)")
        try:
            mcp.run(transport="streamable-http")
        except KeyboardInterrupt:
            print("[MCP] 收到中断信号，正在优雅关闭...")
        finally:
            print("[MCP] 服务器已停止")
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
