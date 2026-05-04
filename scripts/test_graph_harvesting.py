import asyncio
import os
from backend.app.services.intelligence.retrieval.graph.planner import planner_agent
from backend.app.services.intelligence.retrieval.graph.harvester import harvester_node
from backend.app.services.intelligence.retrieval.graph.schema import CourtState

async def test_graph_harvesting():
    print("🚀 [AtomicTest] Starting Graph-based Parallel Harvesting Validation...\n")
    
    # 1. 模拟初始状态
    state: CourtState = {
        "query": "番茄炒蛋先炒蛋还是先炒番茄？",
        "sub_queries": [],
        "evidence_pool": [],
        "agreed_claims": [],
        "conflicts": [],
        "next_step": "PLAN",
        "iteration": 0,
        "final_answer": None
    }
    
    # 2. 节点 A：规划
    plan_update = await planner_agent.plan(state)
    state.update(plan_update)
    
    # 3. 节点 B：并行收割
    print(f"\n⚡ Entering HARVEST node with {len(state['sub_queries'])} sub-queries...")
    harvest_update = await harvester_node.harvest(state)
    
    # 模拟 Reducer：追加证据
    state["evidence_pool"].extend(harvest_update["evidence_pool"])
    state["next_step"] = harvest_update["next_step"]
    
    # 4. 物理确权
    print("\n✅ Harvesting Phase Complete:")
    print(f"   - Evidence Pool Size: {len(state['evidence_pool'])}")
    
    # 检查证据多样性
    local_count = len([e for e in state['evidence_pool'] if e['origin'] == "LOCAL_GALAXY"])
    online_count = len([e for e in state['evidence_pool'] if e['origin'] == "INTERNET_WITNESS"])
    
    print(f"   - Local Sovereignty pieces: {local_count}")
    print(f"   - Online Witness pieces: {online_count}")
    
    if state['evidence_pool']:
        print(f"\n🔍 Sample Evidence from Pool:")
        sample = state['evidence_pool'][0]
        print(f"   - Origin: {sample['origin']}")
        print(f"   - Content: {sample.get('content', '')[:100]}...")
        if 'claims' in sample:
            print(f"   - Atomic Claims: {sample['claims']}")

if __name__ == "__main__":
    os.environ['NO_PROXY'] = 'volces.com,volcengine.com,feishu.cn,bigmodel.cn'
    asyncio.run(test_graph_harvesting())
