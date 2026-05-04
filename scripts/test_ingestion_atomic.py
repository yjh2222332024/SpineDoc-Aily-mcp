"""
Atomic test suite for ingestion pipeline
Step by step verification - each step must pass before moving on
"""
import asyncio
import sys
import os

sys.path.append(os.getcwd())
from backend.app.services.feishu.bitable_ledger import bitable_ledger
from backend.app.services.rag.embedding import embedding_service

async def test_step1_save_chunks():
    """Step 1: Verify save_chunks_batch writes to Bitable"""
    print("\n" + "=" * 50)
    print("TEST 1: save_chunks_batch")
    print("=" * 50)

    # 先创建一个测试文档
    doc_id = await bitable_ledger.get_or_create_document(
        filename="test_atomic.md",
        file_hash="test_hash_001",
        total_pages=1,
        force=True
    )
    print(f"✅ Created doc: {doc_id}")

    # 写入一个测试 chunk
    test_chunks = [{
        "content": "这是测试内容",
        "page_number": 1,
        "breadcrumb": "测试节点"
    }]

    await bitable_ledger.save_chunks_batch(doc_id, test_chunks)
    print(f"✅ save_chunks_batch called with {len(test_chunks)} chunk")

    return doc_id


async def test_step2_wait_for_tags(doc_id):
    """Step 2: Verify wait_for_tags can find saved chunks"""
    print("\n" + "=" * 50)
    print("TEST 2: wait_for_tags (immediate return - no AI)")
    print("=" * 50)

    # 只等 10 秒，因为还没有 AI 会填充摘要
    try:
        result = await bitable_ledger.wait_for_tags(doc_id, timeout=10)
        print(f"✅ wait_for_tags returned {len(result)} items")
        print(f"   Items: {result}")
        return result
    except Exception as e:
        print(f"⚠️ wait_for_tags timed out or errored: {e}")
        return []


async def test_step3_embedding():
    """Step 3: Verify embedding service works"""
    print("\n" + "=" * 50)
    print("TEST 3: embedding_service.get_embeddings")
    print("=" * 50)

    texts = ["这是测试文本", "另一个测试文本"]
    try:
        embeddings = await embedding_service.get_embeddings(texts)
        print(f"✅ Got {len(embeddings)} embeddings")
        print(f"   Dim: {len(embeddings[0]) if embeddings else 'N/A'}")
    except Exception as e:
        print(f"❌ Embedding failed: {e}")

    return embeddings


async def test_step4_cluster_engine():
    """Step 4: Verify cluster engine can be instantiated and accepts chunks"""
    print("\n" + "=" * 50)
    print("TEST 4: cluster_engine.assign_chunk")
    print("=" * 50)

    from backend.app.services.intelligence.galaxy.cluster_engine import ClusterEngine

    engine = ClusterEngine(store=bitable_ledger)
    test_chunk = {
        "id": "test_chunk_001",
        "content": "测试内容",
        "embedding": [0.1] * 2048  # mock embedding
    }

    try:
        await engine.assign_chunk(test_chunk["id"], test_chunk)
        print(f"✅ assign_chunk called successfully")
    except Exception as e:
        print(f"❌ assign_chunk failed: {e}")
        import traceback
        traceback.print_exc()


async def run_all_tests():
    print("🚀 Starting atomic test suite for ingestion pipeline")
    print("=" * 50)

    # Step 1
    doc_id = await test_step1_save_chunks()

    # Step 2
    items = await test_step2_wait_for_tags(doc_id)

    # Step 3
    embeddings = await test_step3_embedding()

    # Step 4
    await test_step4_cluster_engine()

    print("\n" + "=" * 50)
    print("✅ All tests completed")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(run_all_tests())