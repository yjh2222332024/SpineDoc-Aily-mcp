"""
🤖 SpineDoc MCP Server - AI 逻辑质证协议接口
===========================================
职责：提供符合 Model Context Protocol (MCP) 标准的工具集，供 AI 代理直接调用。
架构：属于 Interaction Layer，作为 LLM 与 Backend Engine 之间的标准化桥梁。

工具设计：
  - spinedoc_ingest:    导入文档 → doc_id（幂等）
  - spinedoc_ask:       单文档质证（走 documents→chunks 直路）
  - spinedoc_ask_all:   跨文档质证（走 galaxy→chunks 原逻辑）
  - spinedoc_list_docs: 列出已导入文档
"""

import os
import sys
import json
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP, Context

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.spine_engine import SpineEngine
from backend.app.infra.lark_cli_reporter import LarkCliReporter
from backend.app.infra.memory.amem_adapter import AmemAdapter
from backend.app.services.feishu.bitable_ledger import bitable_ledger

mcp = FastMCP("spinedoc_mcp")


# ─────────────────────────────────────────────────
#  工具 1: 导入文档
# ─────────────────────────────────────────────────

@mcp.tool(
    name="spinedoc_ingest",
    annotations={
        "title": "导入文档到知识库",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
async def spinedoc_ingest(file_path: str, ctx: Context) -> str:
    """
    将文档导入到 SpineDoc 知识库，等待 Bitable AI 完成摘要与标签孵化后返回 doc_id。
    重复导入相同文件会返回已有 doc_id（幂等）。
    支持 PDF 本地文件或飞书云文档 URL。
    """
    await ctx.log_info(f"📥 [MCP] 开始导入文档: {file_path}")

    try:
        reporter = LarkCliReporter()
        memory = AmemAdapter()
        engine = SpineEngine(reporter=reporter, memory=memory)

        await ctx.report_progress(0.1, "正在解析文档...")
        ingest_res = await engine.ingest_document(file_path)

        doc_id = ingest_res.get("id", "")
        filename = ingest_res.get("filename", Path(file_path).name)
        status = ingest_res.get("status", "unknown")

        result = {
            "doc_id": doc_id,
            "filename": filename,
            "status": status,
            "chunk_count": ingest_res.get("chunk_count", 0),
        }
        await ctx.log_info(f"✅ [MCP] 导入完成: {filename} → {doc_id[:16]}...")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f"❌ [MCP] 导入失败: {str(e)}"
        await ctx.log_error(error_msg)
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


# ─────────────────────────────────────────────────
#  工具 2: 单文档质证
# ─────────────────────────────────────────────────

@mcp.tool(
    name="spinedoc_ask",
    annotations={
        "title": "对已导入文档进行逻辑质证",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
    }
)
async def spinedoc_ask(doc_id: str, query: str, ctx: Context) -> str:
    """
    对已导入到知识库的单个文档发起逻辑质证，返回判决书与证据溯源。
    内部走 documents→chunks 直路，不经过星系路由，速度更快。
    doc_id 从 spinedoc_ingest 或 spinedoc_list_docs 获取。
    """
    await ctx.log_info(f"🔍 [MCP] 单文档质证 | doc_id={doc_id[:16]}... | query={query[:40]}...")

    try:
        reporter = LarkCliReporter()
        memory = AmemAdapter()
        engine = SpineEngine(reporter=reporter, memory=memory)

        await ctx.report_progress(0.2, "正在执行逻辑质证...")

        # hybrid_ask 返回 List[Dict]: [0]=主结果, [1:]=证据溯源
        raw_results = await engine.hybrid_ask(
            query=query,
            doc_id=doc_id,
            return_card=False,
        )

        await ctx.report_progress(0.8, "正在封装报文...")

        # 主结果
        main = raw_results[0] if raw_results else {}
        result_meta = main.get("result_metadata", {})

        verdict = {
            "text": main.get("text", "无结论"),
            "confidence": result_meta.get("confidence", 0.0),
            "color": main.get("color", "YELLOW"),
            "cited_sources": result_meta.get("cited_sources", []),
        }

        # 证据溯源
        evidence_trace = []
        for item in raw_results[1:]:
            evidence_trace.append({
                "text": item.get("text", "")[:200],
                "breadcrumb": item.get("breadcrumb", ""),
                "page_number": item.get("page_number", 0),
                "color": item.get("color", "YELLOW"),
                "confidence": item.get("confidence", 0.0),
                "origin": item.get("origin", "UNKNOWN"),
            })

        output = {
            "verdict": verdict,
            "evidence_trace": evidence_trace,
            "evidence_count": len(evidence_trace),
            "phase_log": main.get("phase_log", []),
        }

        await ctx.log_info(f"✅ [MCP] 单文档质证完成 | confidence={verdict['confidence']:.2f} | evidence={evidence_trace}")
        return json.dumps(output, ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f"❌ [MCP] 质证失败: {str(e)}"
        await ctx.log_error(error_msg)
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


# ─────────────────────────────────────────────────
#  工具 3: 跨文档质证
# ─────────────────────────────────────────────────

@mcp.tool(
    name="spinedoc_ask_all",
    annotations={
        "title": "跨全部文档进行逻辑质证",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
    }
)
async def spinedoc_ask_all(query: str, ctx: Context) -> str:
    """
    跨全部已导入文档进行逻辑质证，走 galaxy→chunks 星系路由路径。
    适用于需要对比多份文档或查找跨文档关联的场景。
    """
    await ctx.log_info(f"🔍 [MCP] 跨文档质证 | query={query[:40]}...")

    try:
        reporter = LarkCliReporter()
        memory = AmemAdapter()
        engine = SpineEngine(reporter=reporter, memory=memory)

        await ctx.report_progress(0.2, "正在执行跨文档逻辑质证...")

        raw_results = await engine.hybrid_ask(
            query=query,
            doc_id="all",
            return_card=False,
        )

        await ctx.report_progress(0.8, "正在封装报文...")

        main = raw_results[0] if raw_results else {}
        result_meta = main.get("result_metadata", {})

        verdict = {
            "text": main.get("text", "无结论"),
            "confidence": result_meta.get("confidence", 0.0),
            "color": main.get("color", "YELLOW"),
            "cited_sources": result_meta.get("cited_sources", []),
        }

        evidence_trace = []
        for item in raw_results[1:]:
            evidence_trace.append({
                "text": item.get("text", "")[:200],
                "breadcrumb": item.get("breadcrumb", ""),
                "page_number": item.get("page_number", 0),
                "color": item.get("color", "YELLOW"),
                "confidence": item.get("confidence", 0.0),
                "origin": item.get("origin", "UNKNOWN"),
            })

        output = {
            "verdict": verdict,
            "evidence_trace": evidence_trace,
            "evidence_count": len(evidence_trace),
            "phase_log": main.get("phase_log", []),
        }

        await ctx.log_info(f"✅ [MCP] 跨文档质证完成 | confidence={verdict['confidence']:.2f}")
        return json.dumps(output, ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f"❌ [MCP] 质证失败: {str(e)}"
        await ctx.log_error(error_msg)
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


# ─────────────────────────────────────────────────
#  工具 4: 列出已导入文档
# ─────────────────────────────────────────────────

@mcp.tool(
    name="spinedoc_list_docs",
    annotations={
        "title": "列出知识库中所有文档",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
    }
)
async def spinedoc_list_docs(ctx: Context) -> str:
    """
    列出知识库中所有已导入的文档及其基本信息（文件名、处理状态、总页数）。
    返回的 doc_id 可用于 spinedoc_ask 工具。
    """
    await ctx.log_info("📋 [MCP] 列出所有文档")

    try:
        docs = await bitable_ledger.list_documents()
        output = {
            "documents": docs,
            "total": len(docs),
        }
        return json.dumps(output, ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f"❌ [MCP] 列出文档失败: {str(e)}"
        await ctx.log_error(error_msg)
        return json.dumps({"status": "error", "message": error_msg}, ensure_ascii=False)


# ─────────────────────────────────────────────────
#  运行入口
# ─────────────────────────────────────────────────

def main():
    """MCP server entry point for pyproject.toml scripts."""
    mcp.run()


if __name__ == "__main__":
    main()
