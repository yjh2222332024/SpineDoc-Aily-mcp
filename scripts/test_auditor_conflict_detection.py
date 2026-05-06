import asyncio
from backend.app.services.intelligence.retrieval.graph.auditor import auditor_node
from backend.app.services.intelligence.retrieval.graph.schema import CourtState

async def test_conflict_detection():
    print(" [AtomicTest] Starting AuditorNode Conflict Detection Validation...")
    
    # 1. 模拟注入冲突证据 (Synthetic Contradiction)
    state: CourtState = {
        "query": "番茄炒蛋怎么做？",
        "sub_queries": [],
        "evidence_pool": [
            {
                "id": "E1_LOCAL",
                "claims": ["建议先炒蛋，盛出后再炒番茄"],
                "content": "本地文档：鸡蛋一定要先炒熟...",
                "origin": "LOCAL_GALAXY"
            },
            {
                "id": "E2_ONLINE",
                "claims": ["最新的研究建议先炒番茄，再倒入蛋液"],
                "content": "联网证人：先炒番茄能保留更多番茄红素...",
                "origin": "INTERNET_WITNESS"
            },
            {
                "id": "E3_STABLE",
                "claims": ["加白糖可以中和番茄的酸味"],
                "content": "常识：白糖是灵魂...",
                "origin": "LOCAL_GALAXY"
            }
        ],
        "L3_archive": [],
        "claim_weights": {},
        "agreed_claims": [],
        "conflicts": [],
        "next_step": "AUDIT",
        "iteration": 1,
        "final_answer": None
    }
    
    # 2. 执行审计
    print("\n Executing AUDIT node...")
    update = await auditor_node.audit(state)
    
    # 3. 物理确权
    conflicts = update.get("conflicts", [])
    weights = update.get("claim_weights", {})
    
    print("\n Audit Complete:")
    print(f"   - Conflicts Found: {len(conflicts)}")
    for c in conflicts:
        print(f"     ↳ Topic: {c['topic']} | Desc: {c['description']}")
    
    print(f"   - Weights Initialized: {len(weights)}")
    print(f"   - Next Step: {update['next_step']}")

if __name__ == "__main__":
    asyncio.run(test_conflict_detection())
