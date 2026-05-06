"""
🧪 联邦法庭查询测试
"""
import asyncio
from backend.app.services.intelligence.court.federated_court import FederatedCourt

async def test_query():
    query = "武汉大学国家网络安全学院推免规则"
    print(f" 测试查询：{query}")
    print("=" * 80)

    court = FederatedCourt()
    result = await court.answer_query(query)

    print("\n" + "=" * 80)
    print("📋 法庭裁决结果:")
    print("=" * 80)
    print(result)

if __name__ == "__main__":
    asyncio.run(test_query())
