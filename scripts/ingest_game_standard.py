
import asyncio
import os
import sys
from pathlib import Path

# 确保能找到 backend 模块
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.app.services.spine_engine import SpineEngine

async def run_standard_ingestion():
    """
    SpineDoc 物理脊梁专项审计
    目标：游戏收费乱象研究与治理.pdf (有内置目录)
    """
    engine = SpineEngine()
    doc_path = "ceshi_ocr/游戏收费乱象研究与治理.pdf"
    
    if not os.path.exists(doc_path):
        print(f"❌ [Audit] 找不到目标文件: {doc_path}")
        return

    print(f"\n🚀 [Audit] 启动物理脊梁收割：{doc_path}")
    print(f"🛠️ [Audit] 策略：提取内置 TOC -> 物理页码对齐 -> 高精度区间采样\n")

    try:
        # 使用 force=True 触发新逻辑
        result = await engine.ingest_document(doc_path, force=True)
        
        print("\n" + "🎮" * 20)
        print(f"✅ [Audit] 任务圆满完成！")
        print(f"🔗 Bitable ID: {result.get('bitable_id')}")
        
        toc = result.get('toc', [])
        print(f"📁 物理脊梁项: {len(toc)}")
        # 打印前 5 个章节预览
        for node in toc[:5]:
            print(f"     ↳ L{node.level} {node.title} (P{node.physical_start}-P{node.physical_end})")
        if len(toc) > 5:
            print(f"     ... 以及另外 {len(toc)-5} 个章节")
        print("🎮" * 20)
        
    except Exception as e:
        print(f"\n❌ [Audit] 任务崩溃: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_standard_ingestion())
