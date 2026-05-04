import asyncio
import json
import os
from backend.app.services.intelligence.clustering.scout import scout
from backend.app.services.feishu.bitable_ledger import bitable_ledger

async def run_evolution_demo():
    print("🔭 [Demo] 正在连接飞书 Bitable 主权账本...")
    
    # 1. 探测现状
    galaxies = await scout._fetch_all_galaxies()
    print(f"📊 当前云端星系数量: {len(galaxies)}")
    for g in galaxies:
        print(f"   - {g['name']} (成员: {g['member_count']})")

    # 2. 构造一个测试分片
    # 场景：这是一个关于“逻辑重构”的知识点
    test_chunk = {
        "record_id": "demo_chunk_rec_id", # 假设已经在 Bitable 里的 ID
        "summary": "探讨如何通过无状态架构实现系统的语义演化与逻辑归档。",
        "logic_tags": ["架构设计", "无状态", "重构"],
        "embedding": [0.1] * 1024 # 模拟一个 1024 维向量
    }
    
    # 注意：为了让演示跑通，我们需要一个真实的 Bitable Chunk ID
    # 这里我们先随机取一个已有的 Chunk 进行关联测试，或者仅仅观察 Galaxy 的变化
    print("\n🚀 [Demo] 开始投射测试分片...")
    print(f"   标签: {test_chunk['logic_tags']}")
    
    # 我们直接调用核心投射方法
    # 注意：执行该方法会尝试更新 Bitable
    try:
        await scout.project_chunk_to_galaxy(test_chunk)
        print("\n✅ [Demo] 演化逻辑执行完成。")
    except Exception as e:
        print(f"\n❌ [Demo] 演化失败: {str(e)}")

    # 3. 验证变化
    print("\n🔄 [Demo] 正在拉取演化后的最新状态...")
    new_galaxies = await scout._fetch_all_galaxies()
    for g in new_galaxies:
        print(f"   - {g['name']} (新成员数: {g['member_count']})")

if __name__ == "__main__":
    asyncio.run(run_evolution_demo())
