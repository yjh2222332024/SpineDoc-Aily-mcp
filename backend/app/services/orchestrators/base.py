from typing import List, Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class IngestContext:
    file_path: str
    file_hash: str
    filename: str
    total_pages: int

class BaseIngestOrchestrator:
    """
    负责文档入库编排的基类。
    """
    def __init__(self, engine, store):
        self.engine = engine
        self.store = store

async def _finalize_ingestion(
    db_doc,
    toc: List,
    chunks: List,
    engine: "SpineEngine",
    skip_bitable: bool = False,
    store=None,
) -> Dict[str, Any]:
    """
    云原生确权流水线：
    1. Bitable 账本存入 
    2. 等待 AI 摘要回填 
    3. 云端向量计算 
    4. 星系自动聚类
    """
    from backend.app.services.rag.embedding import embedding_service
    from backend.app.services.intelligence.galaxy.cluster_engine import cluster_engine
    
    doc_record_id = None
    if not skip_bitable:
        try:
            print(f"🛰️ [Finalize] 正在同步资产至 Bitable 云端...")
            doc_record_id = await store.get_or_create_document(
                db_doc.filename, db_doc.file_hash or "", db_doc.total_pages
            )
            
            if toc:
                toc_data = [n.model_dump() if hasattr(n, 'model_dump') else n for n in toc]
                await store.save_toc_items_batch(doc_record_id, toc_data)
            
            await store.save_chunks_batch(doc_record_id, chunks)
            print("✅ [Finalize] 逻辑账本同步完成，等待云端打标...")

            # 2. 等待异步打标回填 (Summary + Tags)
            synced_chunks = await store.wait_for_tags(doc_record_id)
            if not synced_chunks:
                print("⚠️ [Finalize] 打标回填超时或为空。")
            else:
                # 🛡️ 逻辑确权：清洗数据
                valid_chunks = [c for c in synced_chunks if c.get("summary") and len(c.get("summary")) > 2]

                if not valid_chunks:
                    print("⚠️ [Finalize] 没有可用的逻辑摘要分片，跳过聚类。")
                else:
                    # 3. 向量确权
                    print(f"🧠 [Finalize] 正在为 {len(valid_chunks)} 个有效分片计算云端向量...")
                    summary_texts = [c["summary"] for c in valid_chunks]
                    embeddings = await embedding_service.get_embeddings(summary_texts)

                    # 4. 星系聚类 (Galaxy Distribution)
                    print(f"🌌 [Finalize] 启动星系聚类 (Galaxy Clustering)...")
                    for i, c in enumerate(valid_chunks):
                        c["embedding"] = embeddings[i]
                        await cluster_engine.assign_chunk(c["id"], c)

                    # 🚀 [V100.0] 确权闭环：回填最终状态
                    await store.update_document_status(doc_record_id, "COMPLETED")
                    print(f"🏁 [Finalize] 文档 {db_doc.filename} 全量确权入库完毕。")

        except Exception as e:
            print(f"⚠️ [Finalize] 确权流程异常: {e}")
            import traceback
            traceback.print_exc()

    return {"id": str(db_doc.id), "toc": toc, "bitable_id": doc_record_id}

async def _check_duplicate_and_commit(db_doc, store) -> bool:
    """占位符，保持接口兼容"""
    return False

def split_tiered_to_page_map(chunks: List[Dict]) -> Dict:
    """占位符，保持接口兼容"""
    return {}
