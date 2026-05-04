import asyncio
import json
from backend.app.services.intelligence.retrieval.local_retriever import SovereignSentry

async def test_fallback():
    sentry = SovereignSentry()
    
    # 构造一个极其宏观的提问，旨在触发金字塔回退
    query = "番茄炒蛋的核心理念和制作哲学是什么？"
    print(f"🚀 [AtomicTest] Starting Pyramid Fallback Validation for: {query}\n")
    
    # 执行质询
    evidence = await sentry.route_query(query, limit=3)
    
    if evidence:
        print(f"\n✅ Success! Harvested {len(evidence)} evidence chunks:")
        for i, e in enumerate(evidence):
            content = e.get('content', '')
            score = e.get('score', 0.0)
            
            # 判断是否为 L1 共识节点
            is_consensus = "🌌" in content or "共识" in content
            
            print(f"   [{i+1}] Type: {'🔼 CONSENSUS' if is_consensus else '📄 DETAIL'}")
            print(f"       Score: {score:.4f}")
            print(f"       Content: {content[:100]}...")
    else:
        print("⚠️ No evidence harvested.")

if __name__ == "__main__":
    asyncio.run(test_fallback())
