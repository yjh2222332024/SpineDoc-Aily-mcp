import asyncio
from backend.app.services.intelligence.retrieval.local_retriever import SovereignSentry

async def test_routing():
    sentry = SovereignSentry()
    
    queries = [
        "番茄炒蛋怎么做？",
        "系统的架构设计原则是什么？",
        "如何处理 Bitable API 的限频问题？"
    ]
    
    print("🚀 [AtomicTest] Starting SovereignSentry Routing Validation...\n")
    
    for q in queries:
        print(f"🔍 Testing Query: {q}")
        territories = await sentry.route_query(q)
        
        if territories:
            print(f"✅ Success! Locked territories:")
            for t in territories:
                print(f"   - {t['source_name']} (Score: {t.get('score', 0.0):.2f})")
        else:
            print("⚠️ No territories locked. (Expected if matching data is sparse)")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_routing())
