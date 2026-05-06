import asyncio
import os
from backend.app.services.intelligence.retrieval.graph.evolution import evolution_node
from backend.app.services.intelligence.retrieval.graph.schema import CourtState

async def test_evolution_logic():
    print(" [AtomicTest] Starting EvolutionNode Logic Validation...\n")
    
    # 1. 模拟宣判后的状态
    state: CourtState = {
        "query": "番茄炒蛋怎么做？",
        "verdict": {
            "internal_consensus": [
                "事实 1：番茄炒蛋先炒蛋能保证鸡蛋鲜嫩",
                "事实 2：白糖可以中和番茄的酸味"
            ],
            "unresolved_conflicts": ["冲突：是否需要加水淀粉"]
        },
        "evidence_pool": [],
        "L3_archive": [],
        "claim_weights": {},
        "agreed_claims": [],
        "next_step": "EVOLVE",
        "iteration": 3,
        "final_answer": None,
        "sub_queries": [],
        "internal_prior": ""
    }
    
    # 2. 执行演化
    print("🧬 Executing EVOLVE node...")
    update = await evolution_node.evolve(state)
    
    # 3. 物理确权
    print("\n Evolution Signal Captured:")
    print(f"   - Next Step: {update.get('next_step')}")
    print(f"   - Knowledge Backfill: Check background logs for ' [Evolution]'")
    
    # 验证是否指向终点
    if update.get("next_step") == "END":
        print("\n🏁 [Success] Logic Court cycle has reached its terminal state.")

if __name__ == "__main__":
    os.environ['NO_PROXY'] = 'volces.com,volcengine.com,feishu.cn,bigmodel.cn'
    asyncio.run(test_evolution_logic())
