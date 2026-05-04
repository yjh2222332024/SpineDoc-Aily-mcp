import asyncio
import sys
import os
from backend.app.services.intelligence.retrieval.graph.auditor import auditor_node
from backend.app.services.intelligence.retrieval.graph.schema import CourtState

async def test_auditor_pruning():
    print("🚀 [AtomicTest] Starting AuditorNode State Pruning Validation...\n")
    
    # 1. 模拟重度状态 (Evidence with long content)
    long_text = "这是一段非常非常长的文档内容..." * 100
    state: CourtState = {
        "query": "测试剪枝",
        "sub_queries": [],
        "evidence_pool": [
            {
                "id": "E1_HEAVY",
                "claims": ["关键主张 A"],
                "content": long_text,
                "origin": "LOCAL_GALAXY"
            }
        ],
        "L3_archive": [],
        "claim_weights": {"E1_HEAVY": 1.0},
        "agreed_claims": [],
        "conflicts": [],
        "next_step": "AUDIT",
        "iteration": 1,
        "final_answer": None
    }
    
    initial_size = sys.getsizeof(str(state["evidence_pool"]))
    print(f"📊 Initial State Size: {initial_size} bytes")
    
    # 2. 执行审计与剪枝
    print("⚖️ Executing AUDIT node with state pruning...")
    update = await auditor_node.audit(state)
    
    # 3. 物理确权
    pruned_pool = update.get("evidence_pool", [])
    final_size = sys.getsizeof(str(pruned_pool))
    
    print(f"\n✅ Pruning Complete:")
    print(f"   - Final State Size: {final_size} bytes")
    print(f"   - Compression Ratio: {(1 - final_size/initial_size)*100:.1f}%")
    
    if pruned_pool:
        print(f"   - Content Check: {pruned_pool[0]['content']}") # Should be [PRUNED]

if __name__ == "__main__":
    os.environ['NO_PROXY'] = 'volces.com,volcengine.com,feishu.cn,bigmodel.cn'
    asyncio.run(test_auditor_pruning())
