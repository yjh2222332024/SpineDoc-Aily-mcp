import asyncio
import os
import json
from backend.app.services.intelligence.retrieval.graph.synthesizer import synthesizer_node
from backend.app.services.intelligence.retrieval.graph.schema import CourtState

async def test_synthesis():
    print("🚀 [AtomicTest] Starting SynthesizerNode Verdict Validation...\n")
    
    # 1. 模拟一个经过审计的状态 (Contains weights and conflicts)
    state: CourtState = {
        "query": "番茄炒蛋先炒蛋还是先炒番茄？",
        "evidence_pool": [
            {
                "id": "E1",
                "claims": ["传统经典做法是先炒鸡蛋，盛出后再炒番茄"],
                "is_sovereign": True,
                "origin": "LOCAL_GALAXY"
            },
            {
                "id": "E2",
                "claims": ["部分新研究表明先炒番茄能保留更多番茄红素"],
                "is_sovereign": False,
                "origin": "INTERNET_WITNESS"
            }
        ],
        "claim_weights": {"E1": 0.9, "E2": 0.4},
        "conflicts": [{"topic": "COOKING_ORDER", "description": "顺序冲突"}],
        "next_step": "SYNTHESIZE",
        "iteration": 2,
        "verdict": None,
        "final_answer": None,
        "sub_queries": [],
        "L3_archive": [],
        "agreed_claims": [],
        "internal_prior": ""
    }
    
    # 2. 执行宣判
    update = await synthesizer_node.synthesize(state)
    verdict = update.get("verdict", {})
    
    # 3. 物理确权
    print("\n✅ Judge's Verdict (Internal Truth):")
    print(json.dumps(verdict.get("internal_consensus"), indent=4, ensure_ascii=False))
    
    print("\n✅ Assistant's Narrative (User Facing):")
    print(f"   ↳ {verdict.get('assistant_answer')}")
    
    print("\n📊 Citations Check:")
    print(f"   ↳ {verdict.get('citations')}")

if __name__ == "__main__":
    os.environ['NO_PROXY'] = 'volces.com,volcengine.com,feishu.cn,bigmodel.cn'
    asyncio.run(test_synthesis())
