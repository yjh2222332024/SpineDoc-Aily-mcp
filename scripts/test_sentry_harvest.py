import asyncio
import json
from backend.app.services.intelligence.retrieval.sovereign_sentry import SovereignSentry

async def test_harvest():
    sentry = SovereignSentry()
    
    query = "番茄炒蛋需要多少个鸡蛋？"
    print(f"🚀 [AtomicTest] Starting Constrained Harvesting Validation for: {query}\n")
    
    # 执行主权确权收割
    evidence = await sentry.route_query(query, limit=5)
    
    if evidence:
        print(f"\n✅ Success! Harvested {len(evidence)} evidence chunks:")
        for i, e in enumerate(evidence):
            print(f"   [{i+1}] Content: {e.get('content', '')[:50]}...")
            print(f"       RRF Score: {e.get('rrf_score', 0.0):.4f}")
            print(f"       Breadcrumb: {e.get('breadcrumb', 'N/A')}")
            # 验证向量是否正确拉取（懒加载验证）
            if e.get('embedding'):
                print(f"       Vector Check: Found ({len(e['embedding'])} dims)")
            else:
                print(f"       Vector Check: Missing (Lazy loading issue?)")
    else:
        print("⚠️ No evidence harvested.")

if __name__ == "__main__":
    asyncio.run(test_harvest())
