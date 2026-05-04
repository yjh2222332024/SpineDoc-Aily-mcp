
"""
🤖 SpineDoc MCP Server - AI 逻辑质证协议接口
===========================================
职责：提供符合 Model Context Protocol (MCP) 标准的工具集，供飞书 Aily 或其他 AI 代理直接调用。
架构：属于 Interaction Layer，作为 LLM 与 Backend Engine 之间的标准化桥梁。
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field, ConfigDict

# 🏛️ 架构锚定
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

# 导入后端引擎与契约
from backend.app.services.spine_engine import SpineEngine
from backend.app.infra.lark_cli_reporter import LarkCliReporter
from backend.app.infra.memory.amem_adapter import AmemAdapter
from spine_interaction.contracts.verdict import AuditVerdict

# 初始化 MCP 服务器
# 命名规范：{service}_mcp
mcp = FastMCP("spinedoc_mcp")

# --- 1. 输入模型定义 ---

class AuditInput(BaseModel):
    """SpineDoc 逻辑审计工具输入参数"""
    model_config = ConfigDict(str_strip_whitespace=True)

    file_path: str = Field(..., description="文件路径或飞书云端 URL (如: https://xxx.feishu.cn/docx/xxx)")
    query: str = Field(..., description="需要审计的具体逻辑问题 (如: 检查该合同是否存在违约金计算冲突)")
    chat_id: str = Field(..., description="飞书会话 ID，用于结果卡片投射")
    sync_to_bitable: bool = Field(default=True, description="是否将审计结论同步到 Bitable 资产库")

# --- 2. 工具注册 ---

@mcp.tool(
    name="spinedoc_audit",
    annotations={
        "title": "执行逻辑审计",
        "readOnlyHint": False,    # 因为涉及同步到 Bitable，不是纯只读
        "destructiveHint": False,
        "idempotentHint": False   # 每次审计结果可能随知识库进化而不同
    }
)
async def spinedoc_audit(params: AuditInput, ctx: Context) -> str:
    """
    对指定的文档执行深度逻辑一致性审计。
    
    该工具会启动 SpineEngine 逻辑流水线，识别文档中的语义矛盾，
    并将结果以互动卡片的形式发送到指定的飞书会话中。
    同时，它会返回一个结构化的 JSON 报文供 AI 代理进一步分析。
    """
    await ctx.log_info(f"🚀 [MCP] 启动逻辑审计流程 | 问题: {params.query}")
    
    try:
        # 1. 准备基础设施
        reporter = LarkCliReporter()
        memory = AmemAdapter()
        engine = SpineEngine(reporter=reporter, memory=memory)

        await ctx.report_progress(0.1, "正在导入文档并提取脊梁...")
        
        # 2. 调用核心引擎 (Backend Logic)
        ingest_res = await engine.ingest_document(params.file_path)
        doc_id = ingest_res["id"]
        
        await ctx.report_progress(0.4, "正在进行跨维度逻辑质证...")
        
        # 执行联邦质证
        # 这里的结果已经是经过引擎处理的结构化数据
        raw_result = await engine.hybrid_ask(
            query=params.query,
            doc_id=doc_id,
            chat_id=params.chat_id,
            sync_to_bitable=params.sync_to_bitable
        )

        await ctx.report_progress(0.9, "审计完成，正在封装报文...")

        # 3. 契约校验 (Contract Enforcement)
        # 确保输出符合 Interaction Layer 的 Verdict 契约
        res_meta = raw_result.get("result_metadata", {})
        verdict = AuditVerdict(
            id=str(raw_result.get("id", doc_id)),
            query=params.query,
            text=raw_result.get("text", raw_result.get("final_answer", "无结论")),
            confidence=raw_result.get("confidence", 0.0),
            color=raw_result.get("color", "YELLOW"),
            cited_sources=res_meta.get("cited_sources", []),
            phase_meta=res_meta.get("_phase_meta"),
            resolved_conflicts=res_meta.get("resolved_conflicts", [])
        )

        await ctx.log_info("✅ [MCP] 逻辑审计圆满完成，已投射卡片。")
        
        # 返回 JSON 报文给 AI 代理
        return verdict.model_dump_json(indent=2)

    except Exception as e:
        error_msg = f"❌ [MCP] 审计失败: {str(e)}"
        await ctx.log_error(error_msg)
        return json.dumps({"status": "error", "message": error_msg})

# --- 3. 运行配置 ---

if __name__ == "__main__":
    # 默认使用 stdio 模式，方便 Aily 通过命令行直接集成
    mcp.run()
