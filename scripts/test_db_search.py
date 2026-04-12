
import asyncio
from pathlib import Path
from spine_cli.indexer.postgres_store import PostgresStore

async def test_global_search():
    store = PostgresStore()
    print("Testing Global Search (doc_id=None)...")
    results = await store.search("RAG", doc_id=None, limit=5)
    print(f"Results found: {len(results)}")
    for r in results:
        print(f" - Doc: {r.get('doc_id')}, Text: {r.get('text')[:50]}...")

    print("\nTesting Targeted Search (doc_id='doc_2401.14887v4')...")
    # 注意：PostgresStore 现在使用的是 UUID，如果 doc_id 不是 UUID，可能会失败
    # 但我们保持接口兼容性，内部会尝试处理
    results_target = await store.search("RAG", doc_id="doc_2401.14887v4", limit=5)
    print(f"Results found: {len(results_target)}")

if __name__ == "__main__":
    asyncio.run(test_global_search())
