"""
SpineDoc 紧急数据恢复脚本 (Operation: Phoenix)
==============================================
职责：从 OCR 缓存和脊梁 JSON 中重建长文档，绕过 OCR。
"""
import asyncio
import sys
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any

# 🏛️ 路径锚定
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem, Chunk, ProcessingStatus
from backend.app.services.toc.base import SpineNode
from backend.app.services.ingestion.splitter import structural_splitter
from backend.app.services.ingestion.logic_refiner import LogicRefiner
from backend.app.services.rag.vector_store import PostgresStore
from sqlmodel import select

async def restore_document():
    # 1. 加载元数据
    toc_path = "ceshi_ocr/1.pdf.toc_spine.json"
    ocr_path = "ceshi_ocr/1.pdf.ocr_cache.json"
    
    with open(toc_path, "r", encoding="utf-8") as f:
        toc_data = json.load(f)
    with open(ocr_path, "r", encoding="utf-8") as f:
        ocr_cache_raw = json.load(f)
        # 转换为 Dict[int, str]
        ocr_context = {int(k): v for k, v in ocr_cache_raw.items()}

    doc_meta = toc_data["document"]
    filename = doc_meta["filename"]
    
    print(f"🕯️ [Restoration] 准备复活文档: {filename} (406 Pages)")

    sm = get_async_sessionmaker()
    store = PostgresStore()
    refiner = LogicRefiner(threshold=0.25)

    async with sm() as session:
        # A. 创建文档
        db_doc = Document(
            id=uuid.UUID(doc_meta["id"]),
            filename=filename,
            file_path=str(project_root / "ceshi_ocr" / filename),
            file_hash="recovered_from_cache",
            status=ProcessingStatus.PROCESSING,
            total_pages=doc_meta["total_pages"],
            page_offset=doc_meta["page_offset"]
        )
        session.add(db_doc)
        await session.commit()
        await session.refresh(db_doc)

        # B. 转换并入库 TocItems
        spine_nodes = []
        titles = []
        for n in toc_data["spine_nodes"]:
            node = SpineNode(**n)
            spine_nodes.append(node)
            titles.append(node.title)
        
        print(f"  ↳ [Spine] 正在为 {len(titles)} 个目录项生成向量...")
        embeddings = await store.get_embeddings_api(titles)
        
        for i, n in enumerate(spine_nodes):
            session.add(TocItem(
                id=n.id, title=n.title, page=n.logical_page,
                level=n.level, document_id=db_doc.id,
                physical_start=n.physical_start, physical_end=n.physical_end,
                embedding=embeddings[i]
            ))
        await session.flush()

        # C. 物理分片 (利用 ocr_context 绕过真实 PDF)
        print(f"  ↳ [Splitting] 正在从缓存执行语义切片...")
        # 模拟一个 doc 对象，只要能返回 len 即可
        class MockDoc:
            def __len__(self): return doc_meta["total_pages"]
        
        raw_segments = []
        async for seg in structural_splitter.split_by_toc(MockDoc(), spine_nodes, ocr_context=ocr_context):
            raw_segments.append(seg)
        
        print(f"  ↳ [Refining] 正在为 {len(raw_segments)} 个分片打标...")
        refined_chunks = await refiner.refine_batch(filename, spine_nodes, raw_segments)

        # D. 统一入库
        print(f"  ↳ [Finalizing] 正在将证据沉淀至数据库...")
        for i, c in enumerate(refined_chunks):
            session.add(Chunk(
                id=uuid.UUID(c["id"]), content=c["content"], page_number=c["page_number"],
                breadcrumb=c["breadcrumb"], document_id=db_doc.id,
                embedding=c["embedding"], logic_tags=c["logic_tags"],
                metadata_json=c["metadata_json"]
            ))
            if i % 50 == 0: await session.commit()
        
        db_doc.status = ProcessingStatus.COMPLETED
        await session.commit()
        print(f"🏆 [SUCCESS] 文档 {filename} 已通过缓存复活！")

if __name__ == "__main__":
    asyncio.run(restore_document())
