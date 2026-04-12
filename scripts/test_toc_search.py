"""测试 TOC 搜索结果"""
import asyncio
from spine_cli.indexer.postgres_store import PostgresStore

async def test():
    store = PostgresStore()
    
    # 测试 TOC 搜索
    query = "SM4 算法的分组长度是多少？"
    doc_id = "2c91e21b-f6c4-4c94-81f5-57569b353996"
    
    print(f"查询：{query}")
    print(f"文档 ID: {doc_id}")
    print()
    
    toc_results = await store.search_toc(query=query, doc_id=doc_id, limit=5)
    
    print("TOC 搜索结果:")
    for r in toc_results:
        print(f"  P{r['physical_start']}-{r['physical_end']}: {r['title']} (score: {r['score']:.3f})")
    
    print()
    
    # 测试 Chunk 搜索
    chunk_results = await store.search(query=query, doc_id=doc_id, limit=10)
    
    print("Chunk 搜索结果:")
    for r in chunk_results:
        print(f"  P{r['page_number']}: {r['breadcrumb']} ({r['content'][:50]}...)")

asyncio.run(test())
