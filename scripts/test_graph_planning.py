import asyncio
import os
from backend.app.services.intelligence.retrieval.graph.planner import planner_agent
from backend.app.services.intelligence.retrieval.graph.schema import CourtState

async def test_planning():
    print("🚀 [AtomicTest] Starting Graph Planning & State Initialization...")
    
    # 1. 模拟初始化状态 (The Genesis State)
    state: CourtState = {
        "query": "番茄炒蛋先炒蛋还是先炒番茄，有没有什么营养学上的依据？",
        "sub_queries": [],
        "evidence_pool": [],
        "agreed_claims": [],
        "conflicts": [],
        "next_step": "PLAN",
        "iteration": 0,
        "final_answer": None
    }
    
    print(f"📄 Initial Query: {state['query']}")
    
    # 2. 执行 Planner 节点
    update = await planner_agent.plan(state)
    
    # 3. 模拟状态合并 (The Graph Reducer)
    state.update(update)
    
    print("\n✅ State Updated:")
    print(f"   - Sub-queries ({len(state['sub_queries'])}):")
    for sq in state['sub_queries']:
        print(f"     ↳ {sq}")
    print(f"   - Next Step: {state['next_step']}")
    print(f"   - Iteration: {state['iteration']}")

if __name__ == "__main__":
    os.environ['NO_PROXY'] = 'volces.com,volcengine.com,feishu.cn,bigmodel.cn'
    asyncio.run(test_planning())
