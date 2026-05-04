import asyncio
import os
from backend.app.services.intelligence.retrieval.graph.auditor import auditor_node
from backend.app.services.intelligence.retrieval.graph.schema import CourtState

async def test_auditor_debate():
    print("🚀 [AtomicTest] Starting AuditorNode Debate & De-weighting Validation...\n")
    
    # 1. 模拟注入冲突证据 (Synthetic Contradiction)
    state: CourtState = {
        "query": "番茄炒蛋先炒蛋还是先炒番茄？",
        "sub_queries": [],
        "evidence_pool": [
            {
                "id": "E1_LOCAL_SOVEREIGN",
                "claims": ["传统经典做法：建议先炒蛋，盛出后再炒番茄。"],
                "content": "本地菜谱：第一步，热锅凉油下蛋液...",
                "origin": "LOCAL_GALAXY"
            },
            {
                "id": "E2_ONLINE_NOISY",
                "claims": ["非主流做法：建议先炒番茄，不要先炒蛋。"],
                "content": "某自媒体：懒人版番茄炒蛋，不用洗锅直接下蛋...",
                "origin": "INTERNET_WITNESS"
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
    
    # 2. 执行审计与辩论
    print("⚖️ Executing AUDIT node with debate...")
    update = await auditor_node.audit(state)
    
    # 3. 物理确权
    weights = update.get("claim_weights", {})
    active_pool = update.get("evidence_pool", [])
    archive = update.get("L3_archive", [])
    
    print("\n✅ Debate Results:")
    for eid, w in weights.items():
        print(f"   - Evidence {eid}: Weight = {w:.2f}")
    
    print(f"\n📊 State Metabolism:")
    print(f"   - Active Pool Count: {len(active_pool)}")
    print(f"   - L3 Archive Count: {len(archive)}")
    
    if archive:
        print(f"     ↳ Archived ID: {archive[0]['id']} (Due to low weight)")

if __name__ == "__main__":
    os.environ['NO_PROXY'] = 'volces.com,volcengine.com,feishu.cn,bigmodel.cn'
    asyncio.run(test_auditor_debate())
