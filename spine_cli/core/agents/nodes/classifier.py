import fitz
import os
import asyncio
from typing import Dict, Any
from spine_cli.core.agents.state import DocumentState, DocumentType
from backend.app.services.parser import hybrid_parser

def classifier_node(state: DocumentState) -> Dict[str, Any]:
    """
    Classifier Agent (V9.2 HITL Optimized)
    """
    file_path = state.get("file_path")
    if not file_path or not os.path.exists(file_path):
        return {"processing_errors": ["File not found."]}

    # 🚀 核心动作：支持 HITL 模式
    manual_range = state.get("manual_toc_range")
    
    # 获取 Event Loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # 🆕 使用统一的 extract_toc_async 接口
    if loop.is_running():
        import threading
        # 兼容 LangGraph 的线程池执行环境
        toc_items = asyncio.run_coroutine_threadsafe(
            hybrid_parser.extract_toc_async(file_path, manual_range=manual_range), 
            loop
        ).result()
    else:
        toc_items = loop.run_until_complete(
            hybrid_parser.extract_toc_async(file_path, manual_range=manual_range)
        )
    
    doc = fitz.open(file_path)
    total_pages = len(doc)
    doc.close()

    # 根据提取结果判定状态
    doc_type = DocumentType.SCANNED # 默认扫描件
    confidence = 0.9 if len(toc_items) > 5 else 0.5
    
    return {
        "document_type": doc_type,
        "total_pages": total_pages,
        "structured_toc": toc_items, 
        "confidence_score": confidence,
        "current_node": "classifier"
    }
