"""
SpineDoc LogicRefiner 原子测试 (The Test Tube)
===========================================
目的：在完全隔离环境下，验证精炼、打标、向量化三位一体的逻辑。
"""

import asyncio
import sys
from pathlib import Path

# 🏛️ 确保导入路径
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.app.services.rag.logic_refiner import LogicRefiner

TEST_CHUNK = """
海绵结构包括两个阶段，吸水阶段和挤水阶段。
在吸水阶段，对长度为 r 的数据块填充 c 个 0，扩展为 b 位。
然后将结果与状态变量 S 进行异或，作为迭代函数 f 的输入。
SHA-3 的默认值是 c=1024 位，r=576 位。
"""

async def run_atomic_test():
    print("🔬 [Atomic] 正在初始化精炼引擎...")
    refiner = LogicRefiner()
    
    print("🧪 [Atomic] 正在对样本切片进行手术...")
    # 模拟一个符合 Batch 结构的 segment
    segment = {
        "content": TEST_CHUNK,
        "breadcrumb": "测试章节 > 海绵结构",
        "metadata_json": {}
    }
    
    try:
        results = await refiner.refine_batch("测试文档", [], [segment])
        res = results[0]
        
        print("\n" + "="*40)
        print("🏛️ [Atomic] 实验结果报告：")
        print(f"✅ 状态: {res['refine_status']}")
        print(f"🏷️ 语义标签: {', '.join(res['logic_tags'])}")
        
        emb = res['embedding']
        print(f"🧬 向量维度: {len(emb)}")
        print(f"📊 向量前 5 位: {emb[:5]}")
        print(f"📝 摘要预览: {res['summary']}")
        print("="*40)
        
        # 核心断言
        if len(emb) == 1024 and len(res['logic_tags']) > 0:
            print("\n✨ [Atomic] 测试通过！组件已完美对齐。")
        else:
            print("\n❌ [Atomic] 测试失败：维度不匹配或标签丢失。")
            
    except Exception as e:
        print(f"🚨 [Atomic] 测试过程崩溃: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_atomic_test())
