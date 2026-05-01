
import asyncio
import os
import sys
from pathlib import Path

# 确保能找到 backend 模块
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.app.services.spine_engine import SpineEngine

async def test_cloud_ingestion():
    """
    SpineDoc 云端收割实测
    目标：用户提供的飞书 Wiki 链接
    """
    engine = SpineEngine()
    url = "https://jcneyh7qlo8i.feishu.cn/wiki/O27CwF9hiidqkskJixYc3rAFndc?from=from_copylink"
    
    print(f"\n🚀 [CloudAudit] 启动云端知识收割：{url}")
    print(f"🛠️ [CloudAudit] 策略：识别 Wiki URL -> 捕获内容 -> 逻辑确权 -> 影子镜像\n")

    try:
        # 使用 force=True 触发新逻辑
        result = await engine.ingest_document(url, force=True)
        
        print("\n" + "☁️" * 20)
        print(f"✅ [CloudAudit] 知识已成功收缴归库！")
        print(f"🔗 Bitable ID: {result.get('bitable_id')}")
        
        toc = result.get('toc', [])
        print(f"📁 捕获的逻辑脊梁: {len(toc)} 个节点")
        for node in toc:
            print(f"     ↳ [{node.logic_coord}] {node.title}")
        print("☁️" * 20)
        
    except Exception as e:
        print(f"\n❌ [CloudAudit] 任务崩溃: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_cloud_ingestion())
