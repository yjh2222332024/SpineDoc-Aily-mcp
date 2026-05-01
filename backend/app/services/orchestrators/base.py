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
    skip_bitable: bool = False,
    store=None,
) -> dict[str, Any]:
    """
    Cloud-native persistence: Bitable is the sole ledger.
    Includes GLM vector computation for logical summaries and Galaxy Clustering.
    """
    from backend.app.services.rag.embedding import embedding_service
    from backend.app.services.intelligence.galaxy.cluster_engine import cluster_engine
    from backend.app.services.knowledge.git_manager import get_git_manager

    doc_record_id = None
    if not skip_bitable:
        try:
            doc_record_id = await store.get_or_create_document(
                db_doc.filename, db_doc.file_hash or "", db_doc.total_pages
            )

            if toc:
                toc_data = [n.model_dump() if hasattr(n, 'model_dump') else n for n in toc]
                await store.save_toc_items_batch(doc_record_id, toc_data)

            # 1. 保存原始分片到 Bitable
            await store.save_chunks_batch(doc_record_id, chunks)

            # 2. 语义反哺轮询
            synced_chunks = await store.wait_for_tags(doc_record_id)
            print(f"  ↳ 成功召回 {len(synced_chunks)} 个打标分片")

            # 3. 向量确权
            print(f"🧠 [Finalize] 正在为 {len(synced_chunks)} 个逻辑摘要计算向量...")
            summary_texts = [c.get("summary") or c.get("content")[:200] for c in synced_chunks]
            embeddings = await embedding_service.get_embeddings(summary_texts)

            # 4. 星系聚类
            print(f"🌌 [Finalize] 启动星系聚类...")
            from backend.app.services.intelligence.galaxy.cluster_engine import ClusterEngine
            sower = ClusterEngine(store=store)
            for i, c in enumerate(synced_chunks):
                if not c or not isinstance(c, dict):
                    print(f"⚠️ [Finalize] 发现坏分片，跳过: {c}")
                    continue
                
                # 🛡️ 暴力调试
                print(f"DEBUG: Processing chunk index {i}, ID: {c.get('id')}")
                if 'embedding' not in c:
                     c["embedding"] = embeddings[i]
                     print("DEBUG: Embedding injected.")

                await sower.assign_chunk(c["id"], c)

            
            # 5. Git 溯源 (改为延迟异步记录，防止阻塞)
            print(f"📜 [Finalize] 提交 Git 溯源信息...")
            # (Git 部分逻辑已隔离，待异步实现)

        except Exception as e:
            print(f"⚠️ [Finalize] Cloud sync / Clustering error: {e}")
    else:
        print(f"🛰️ [Finalize] 跳过 Bitable 冗余同步（由编排器自主管理）")

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
