import asyncio
import os
from backend.app.services.intelligence.retrieval.federated_logic_court import federated_court

async def test_court():
    print("🚀 [AtomicTest] Starting FederatedLogicCourt Truth Arbitration...\n")
    
    # 场景 1：内部知识完备（架构设计）
    query_local = "系统的架构设计原则是什么？"
    print(f"⚖️ Scenario 1: Local Sovereignty Focus -> {query_local}")
    res1 = await federated_court.arbitrate(query_local)
    print(f"   ↳ Results: {len(res1['evidence'])} items. Has Witness: {res1['has_witness']}")
    print("-" * 30)

    # 场景 2：内部知识可能不足，需要联网（常识/动态信息）
    query_witness = "今天北京的天气如何？" # 故意问一个本地没有的
    print(f"⚖️ Scenario 2: Witness Escalation -> {query_witness}")
    res2 = await federated_court.arbitrate(query_witness)
    print(f"   ↳ Results: {len(res2['evidence'])} items. Has Witness: {res2['has_witness']}")
    if res2['has_witness']:
        print(f"   ↳ Sample Witness Content: {res2['evidence'][-1]['content'][:100]}...")

if __name__ == "__main__":
    # 网络防御
    os.environ['NO_PROXY'] = 'volces.com,volcengine.com,feishu.cn,bigmodel.cn'
    asyncio.run(test_court())
