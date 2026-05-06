import asyncio
import os
import json
from backend.app.services.intelligence.retrieval.experts.online_retriever import WitnessExpert

async def test_witness_retrieval():
    print(" [AtomicTest] Starting WitnessExpert (Online Retrieval) Validation...")
    
    # 确权 API Key
    expert = WitnessExpert()
    
    # 测试 Query：涉及实时信息或通用常识
    queries = ["番茄炒蛋是先炒蛋还是先炒番茄？", "2024年诺贝尔文学奖获得者是谁？"]
    
    for q in queries:
        print(f"\n Testing Query: {q}")
        try:
            # WitnessExpert.retrieve 接收 List[str]
            result = await expert.retrieve([q])
            
            if result.get("evidence_chunks"):
                print(f" Success! Retrieved {len(result['evidence_chunks'])} refined chunks.")
                for i, chunk in enumerate(result['evidence_chunks'][:3]):
                    print(f"\n--- [Evidence {i+1}] ---")
                    print(f"   Source: {chunk.get('source_title', 'N/A')}")
                    print(f"   Stability: {chunk.get('stability', 0.0):.2f}")
                    print(f"   Logic Confidence: {chunk.get('confidence', 0.0):.3f} ({chunk.get('color')})")
                    
                    claims = chunk.get('claims', [])
                    print(f"    Atomic Claims ({len(claims)}):")
                    for j, claim in enumerate(claims):
                        print(f"      {j+1}. {claim}")
                    
                    print(f"    Raw Snippet: {chunk.get('content', '')[:100]}...")
            else:
                print(f" Warning: No evidence found for this query. Error: {result.get('error')}")
                
        except Exception as e:
            print(f" Exception during retrieval: {e}")

if __name__ == "__main__":
    # 网络防御
    os.environ['NO_PROXY'] = 'volces.com,volcengine.com,feishu.cn,bigmodel.cn'
    asyncio.run(test_witness_retrieval())
