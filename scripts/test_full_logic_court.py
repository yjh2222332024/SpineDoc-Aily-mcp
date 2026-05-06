import asyncio
import os
import json
from backend.app.services.intelligence.retrieval.graph.coordinator import logic_court

async def test_full_court_integration():
    print(" [IntegrationTest] Launching End-to-End Sovereign Logic Court Process...\n")
    
    # 模拟真实用户质询
    query = "如何制作一份营养均衡且地道的番茄炒蛋？"
    
    # 执行全链路
    print(f" Query: {query}")
    final_state = await logic_court.run(query)
    
    # 物理确权报告
    print("\n" + "="*50)
    print(" FINAL JUDGEMENT REPORT")
    print("="*50)
    
    verdict = final_state.get("verdict", {})
    
    print(f" Assistant Answer:")
    print(f"   ↳ {verdict.get('assistant_answer')}")
    
    print(f"\n🧠 Internal Consensus ({len(verdict.get('internal_consensus', []))} facts):")
    for fact in verdict.get('internal_consensus', []):
        print(f"   - {fact}")
        
    print(f"\n📊 System Metabolism Statistics:")
    print(f"   - Total Iterations: {final_state['iteration']}")
    print(f"   - Active Evidence: {len(final_state['evidence_pool'])}")
    print(f"   - Archived Noise (L3): {len(final_state['L3_archive'])}")
    print(f"   - Unresolved Conflicts: {len(verdict.get('unresolved_conflicts', []))}")
    
    print("\n🏁 Integration validation complete.")

if __name__ == "__main__":
    # 环境确权
    os.environ['NO_PROXY'] = 'volces.com,volcengine.com,feishu.cn,bigmodel.cn'
    asyncio.run(test_full_court_integration())
