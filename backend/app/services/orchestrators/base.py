async def _finalize_ingestion(
    db_doc,
    toc: List,
    chunks: List,
    engine: "SpineEngine",
    skip_bitable: bool = False,
    store=None,
) -> dict[str, Any]:
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
                # 3. 向量确权
                print(f"🧠 [Finalize] 正在计算 {len(synced_chunks)} 个分片的逻辑向量...")
                summary_texts = [c.get("summary") for c in synced_chunks]
                embeddings = await embedding_service.get_embeddings(summary_texts)
                
                # 4. 星系聚类
                print(f"🌌 [Finalize] 启动星系聚类...")
                for i, c in enumerate(synced_chunks):
                    c["embedding"] = embeddings[i]
                    await cluster_engine.assign_chunk(c["id"], c)
        except Exception as e:
            print(f"⚠️ [Finalize] 确权流程异常: {e}")
            import traceback
            traceback.print_exc()

    return {"id": str(db_doc.id), "toc": toc, "bitable_id": doc_record_id}
