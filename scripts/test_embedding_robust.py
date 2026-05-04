import asyncio
import os
import sys
from pathlib import Path

# 确权环境
sys.path.append(str(Path(__file__).parent.parent))

from backend.app.services.ingestion.embedding import embedding_service
from backend.app.core.config import settings

async def test_basics():
    print("\n🧪 [Test] 基础连通性验证...")
    test_text = "这是一段用于确权的测试文本"
    try:
        vecs = await embedding_service.get_embeddings([test_text])
        if vecs and len(vecs[0]) == settings.EMBEDDING_DIMENSION:
            print(f"✅ 连通性通过！获得维数: {len(vecs[0])}")
        else:
            print(f"❌ 维数不符：预期 {settings.EMBEDDING_DIMENSION}, 实际 {len(vecs[0]) if vecs else 0}")
    except Exception as e:
        print(f"❌ 连通性失败: {e}")

async def test_batching():
    print("\n🧪 [Test] 批量处理压力测试...")
    # 构造 50 个短句，这通常会触发 400 错误，除非有分批逻辑
    test_texts = [f"测试文本片段 NO.{i}" for i in range(50)]
    try:
        vecs = await embedding_service.get_embeddings(test_texts)
        if len(vecs) == 50:
            print(f"✅ 批量测试通过！成功获取 {len(vecs)} 个向量。")
        else:
            print(f"❌ 数量不符：预期 50, 实际 {len(vecs)}")
    except Exception as e:
        print(f"❌ 批量测试失败: {e}")

if __name__ == "__main__":
    print("🛡️ SpineDoc 向量确权工作组启动...")
    print(f"📍 API URL: {settings.EMBEDDING_BASE_URL}")
    print(f"📍 MODEL: {settings.EMBEDDING_MODEL_NAME}")
    
    asyncio.run(test_basics())
    asyncio.run(test_batching())
