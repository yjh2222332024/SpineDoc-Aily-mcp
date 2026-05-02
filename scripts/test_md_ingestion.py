
import asyncio
import os
import sys
from pathlib import Path

# 确保能找到 backend 模块
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.app.services.spine_engine import SpineEngine

async def test_md_ingestion():
    """
    SpineDoc Markdown 物理脊梁专项审计
    目标：docs/20260409_dev_log.md
    """
    engine = SpineEngine()
    doc_path = "docs/20260409_dev_log.md"
    
    if not os.path.exists(doc_path):
        print(f"❌ [Audit] 找不到目标文件: {doc_path}")
        return

    print(f"\n🚀 [Audit] 启动 Markdown 物理脊梁收割：{doc_path}")
    print(f"🛠️ [Audit] 策略：检测后缀 -> 提取 # 标题 -> Bitable 炼金 -> 影子渲染\n")

    try:
        # 使用 force=True 触发新逻辑
        result = await engine.ingest_document(doc_path, force=True)
        
        print("\n" + "📝" * 20)
        print(f"✅ [Audit] 任务圆满完成！")
        print(f"🔗 Bitable ID: {result.get('bitable_id')}")
        
        toc = result.get('toc', [])
        print(f"📁 识别到的标题项: {len(toc)}")
        for node in toc:
            source_tag = "[Physical]" if node.source == "markdown" else "[Synthetic]"
            print(f"     ↳ {source_tag} L{node.level} {node.title}")
        print("📝" * 20)
        
    except Exception as e:
        print(f"\n❌ [Audit] 任务崩溃: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_md_ingestion())
