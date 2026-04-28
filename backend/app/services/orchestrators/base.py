from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from uuid import UUID
import re

from backend.app.core.models import TocItem, Chunk, ProcessingStatus


@dataclass
class IngestContext:
    """摄入选项组"""
    force: bool = False
    force_ocr: bool = False
    limit_pages: Optional[int] = None
    manual_toc_range: Optional[List[int]] = None
    manual_offset: Optional[int] = None
    content_md: Optional[str] = None


class BaseIngestOrchestrator(ABC):
    """基类：定义摄入管道入口"""

    @abstractmethod
    async def ingest(
        self,
        file_path: str,
        file_hash: str,
        session_maker,
        engine: "SpineEngine",
        ctx: Optional[IngestContext] = None,
    ) -> dict[str, Any]:
        ...


def split_tiered_to_page_map(
    markdown: str,
) -> Dict[int, str]:
    """
    将三级加载器的整份 Markdown 拆分为页级文本映射。
    返回 {page_index: text}，page_index 从 0 开始。
    """
    anchor_pattern = re.compile(
        r'<!--\s*page\s+content="([^"]*)"\s*-->',
        re.IGNORECASE,
    )
    anchors = list(anchor_pattern.finditer(markdown))
    if not anchors:
        return {}

    result: Dict[int, str] = {}
    for i, m in enumerate(anchors):
        page_match = re.search(r'P(\d+)', m.group(1))
        if not page_match:
            continue
        page_idx = int(page_match.group(1)) - 1

        start = m.end()
        end = anchors[i + 1].start() if i + 1 < len(anchors) else len(markdown)
        text = markdown[start:end].strip()
        if text:
            result[page_idx] = text

    return result


async def _finalize_ingestion(
    db_doc,
    toc: List,
    chunks: List,
    engine: "SpineEngine",
) -> dict[str, Any]:
    """
    🚀 [V95.0] 云端主权持久化：彻底废弃本地 DB 与向量化。
    """
    from backend.app.services.feishu.bitable_ledger import bitable_ledger
    
    # 1. Bitable 同步 (唯一账本)
    doc_record_id = None
    try:
        print(f"🛰️ [Finalize] 正在同步资产至 Bitable 云端...")
        doc_record_id = await bitable_ledger.get_or_create_document(
            db_doc.filename, db_doc.file_hash or "", db_doc.total_pages
        )
        
        if toc:
            toc_data = [n.model_dump() if hasattr(n, 'model_dump') else n for n in toc]
            await bitable_ledger.save_toc_items_batch(doc_record_id, toc_data)
        
        await bitable_ledger.save_chunks_batch(doc_record_id, chunks)
        print("✅ [Finalize] 飞书 Bitable 逻辑账本同步完成")
    except Exception as e:
        print(f"⚠️ [Finalize] 云端同步异常: {e}")

    # 🏛️ 架构师决定：本地数据库写入与向量化已废弃，直接跳过。

    # 2. 记忆进化 (可选)
    try:
        all_evolution_logs = []
        for c in chunks:
            # 兼容字典和对象格式
            c_id = c.get("id") if isinstance(c, dict) else getattr(c, "id", None)
            c_content = c.get("content") if isinstance(c, dict) else getattr(c, "content", "")
            
            note_id = await engine.memory.ingest_memory({
                "id": str(c_id), "content": c_content,
                "document_id": str(db_doc.id),
            })
            if note_id:
                logs = await engine.memory.evolve_network(note_id)
                all_evolution_logs.extend(logs)

        if all_evolution_logs:
            await engine.reporter.report_evolution(all_evolution_logs)
    except Exception as e:
        print(f"⚠️ [Memory] 进化记录跳过: {e}")

    return {"id": str(db_doc.id), "toc": toc, "bitable_id": doc_record_id}


async def _check_duplicate_and_commit(
    file_path: str,
    file_hash: str,
    force: bool,
    session_maker,
) -> Optional[dict[str, Any]]:
    """
    🚀 [V95.0] 主权移交：本地不再执行去重逻辑，交由 Bitable 账本处理。
    """
    return None
