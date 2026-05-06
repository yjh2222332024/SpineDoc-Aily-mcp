from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from uuid import UUID
import re
import asyncio
import json
from uuid import uuid4

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
        tag_timeout: int = 300
    ) -> dict[str, Any]:
        ...

def split_tiered_to_page_map(markdown: str) -> Dict[int, str]:
    anchor_pattern = re.compile(r'<!--\s*page\s+content="([^"]*)"\s*-->', re.IGNORECASE)
    anchors = list(anchor_pattern.finditer(markdown))
    if not anchors: return {}
    result: Dict[int, str] = {}
    for i, m in enumerate(anchors):
        page_match = re.search(r'P(\d+)', m.group(1))
        if not page_match: continue
        page_idx = int(page_match.group(1)) - 1
        start = m.end()
        end = anchors[i + 1].start() if i + 1 < len(anchors) else len(markdown)
        text = markdown[start:end].strip()
        if text: result[page_idx] = text
    return result

async def _compute_embeddings_and_cluster(synced_chunks: List[Dict], store, doc_record_id: Optional[str] = None, engine=None):
    """
     [V105.0] 核心确权：执行向量计算（基于 Bitable AI 摘要与标签）、星系聚类与 A-MEM 记忆演进。
    """
    from backend.app.services.ingestion.embedding import embedding_service
    from backend.app.services.intelligence.clustering.cluster_engine import cluster_engine
    
    # 1. 逻辑确权：清洗数据
    valid_chunks = [c for c in synced_chunks if c.get("summary") and len(c.get("summary")) > 2]
    if not valid_chunks:
        print(" [_compute] 逻辑摘要缺失，无法执行聚类。")
        return

    # 2. 向量确权：基于 Bitable AI 孵化的字段内容进行向量化
    print(f"🧠 [_compute] 正在对 {len(valid_chunks)} 个由 Bitable AI 孵化的分片执行向量化聚类...")
    
    #  架构师守则：向量化必须融合“逻辑摘要”与“语义标签”，这是最深层的语义表达
    to_embed = []
    for c in valid_chunks:
        tags_str = " ".join(c.get("logic_tags", []))
        # 融合摘要与标签
        text_for_embedding = f"{c['summary']} {tags_str}"
        to_embed.append(text_for_embedding)

    if to_embed:
        embeddings = await embedding_service.get_embeddings(to_embed)
        # 将算好的向量注入，并回填到 Bitable
        for i, c in enumerate(valid_chunks):
            vector = embeddings[i]
            c["embedding"] = vector
            #  物理确权：回填向量到 Bitable “向量表征”字段
            await store.update_chunk_fields(c["id"], {"向量表征": json.dumps(vector)})
    
    # 3. 星系聚类与 A-MEM 协同
    print(f"🌌 [_compute] 启动双重确权：星系分配 + 记忆演进...")
    for i, c in enumerate(valid_chunks):
        vector = c["embedding"]
        
        # A. 星系确权 (RAPTOR 核心)
        await cluster_engine.assign_chunk(c["id"], c)
        
        # B. A-MEM 确权 (找回丢失的灵魂)
        if engine and hasattr(engine, "memory"):
            try:
                note_id = await engine.memory.ingest_memory({
                    "id": c["id"], 
                    "content": c.get("content", ""),
                    "document_id": doc_record_id,
                    "embedding": vector,
                    "logic_tags": c.get("logic_tags", [])
                })
                if note_id: 
                    await engine.memory.evolve_network(note_id)
                    #  物理确权：回填记忆 ID 到 Bitable
                    await store.update_chunk_fields(c["id"], {"记忆ID": str(note_id)})
            except Exception as e:
                print(f" [Memory] 记忆演进中断: {e}")

    # 4.5 入库冲突检测（新 chunks vs 星系已有知识）
    ingestion_conflicts = await _detect_ingestion_conflicts(valid_chunks, store, engine)
    if ingestion_conflicts:
        print(f"⚠️ [Ingestion] 检测到 {len(ingestion_conflicts)} 处入库冲突")
        if doc_record_id:
            try:
                await store.update_document_fields(doc_record_id, {
                    "处理状态": f"COMPLETED (冲突:{len(ingestion_conflicts)})"
                })
            except Exception:
                pass

    # 4. 状态封印
    if doc_record_id:
        await store.update_document_status(doc_record_id, "COMPLETED")
        print(f"🏁 [_compute] 文档逻辑主权已封印。")

async def _detect_ingestion_conflicts(
    valid_chunks: List[Dict],
    store,
    engine=None,
) -> List[Dict]:
    """
    入库冲突检测：检查新 chunks 是否与星系已有知识矛盾。
    在 _compute_embeddings_and_cluster 内星系分配后调用。
    """
    from backend.app.services.intelligence.retrieval.utils.conflict_detector import ConflictDetector

    detector = ConflictDetector()
    all_conflicts = []

    for c in valid_chunks:
        galaxy_id = c.get("galaxy_id")
        if not galaxy_id:
            continue

        existing = await store.fetch_chunks_by_galaxy(galaxy_id, limit=5, has_summary=True)
        if not existing:
            continue

        source_results = [
            {
                "source_name": f"新文档 {c.get('doc_id', '')[:8]}",
                "doc_id": c.get("doc_id", ""),
                "evidence_chunks": [c],
            },
            {
                "source_name": f"星系 {galaxy_id[:8]}",
                "doc_id": galaxy_id,
                "evidence_chunks": existing,
            },
        ]

        conflicts = await detector.detect(
            source_results,
            query=f"检测 '{c.get('summary', '')[:80]}' 是否与星系已有知识冲突"
        )
        if conflicts:
            for conf in conflicts:
                conf["ingestion_chunk_id"] = c["id"]
                conf["galaxy_id"] = galaxy_id
            all_conflicts.extend(conflicts)

            meta_str = c.get("元数据", "{}")
            try:
                meta = json.loads(meta_str) if isinstance(meta_str, str) else meta_str
            except json.JSONDecodeError:
                meta = {}
            meta["ingestion_conflicts"] = [
                {"description": conf["description"], "severity": conf.get("severity", "MINOR")}
                for conf in conflicts
            ]
            c["元数据"] = json.dumps(meta, ensure_ascii=False)

    return all_conflicts

async def _finalize_ingestion(
    db_doc,
    toc: List,
    chunks: List,
    engine: "SpineEngine",
    skip_bitable: bool = False,
    store=None,
    tag_timeout: int = 300
) -> dict[str, Any]:
    """
    高层确权流水线。
    """
    from backend.app.services.knowledge.git_manager import get_git_manager
    git_manager = get_git_manager()

    doc_record_id = None
    if not skip_bitable:
        try:
            print(f" [Finalize] 资产物理同步...")
            doc_record_id = await store.get_or_create_document(
                db_doc.filename, db_doc.file_hash or "", db_doc.total_pages
            )
            if toc:
                toc_data = [n.model_dump() if hasattr(n, 'model_dump') else n for n in toc]
                await store.save_toc_items_batch(doc_record_id, toc_data)
            
            #  物理确权：获取本次生成的 Record IDs
            created_chunk_ids = await store.save_chunks_batch(doc_record_id, chunks)
            print(f" [Finalize] 逻辑账本已登记 ({len(created_chunk_ids)} 条)，等待语义孵化...")

            # 借力打力：只针对本次生成的 ID 进行轮询
            synced_chunks = await store.wait_for_completion(doc_record_id, created_chunk_ids, timeout=tag_timeout)
            if synced_chunks:
                # 触发深层逻辑会师
                await _compute_embeddings_and_cluster(synced_chunks, store, doc_record_id=doc_record_id, engine=engine)

            # 5. Git 溯源 (批量提交，避免每分片一个 commit)
            print(f"[Finalize] 提交 Git 逻辑指纹 ({len(created_chunk_ids)} 分片, 单次提交)...")
            git_items = []
            for i, c in enumerate(chunks):
                cid = created_chunk_ids[i] if i < len(created_chunk_ids) else str(uuid4())
                git_items.append({
                    "chunk_id": cid,
                    "content": c.get("content", ""),
                    "metadata": {},
                })
            git_manager.commit_chunks_batch(git_items, message=f"Ingestion Sync: {db_doc.filename}")

        except Exception as e:
            print(f" [Finalize] 确权崩溃: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f" [Finalize] 旁路确权开启。")

    return {
        "id": doc_record_id or str(db_doc.id), 
        "toc": toc, 
        "bitable_id": doc_record_id,
        "status": "success",
        "chunk_count": len(chunks)
    }

from uuid import uuid4
