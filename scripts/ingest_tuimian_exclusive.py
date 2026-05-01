
import asyncio
import os
import sys
from pathlib import Path

# 确保能找到 backend 模块
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.app.services.spine_engine import SpineEngine

async def run_exclusive_ingestion():
    """
    SpineDoc 逻辑确权专项审计 - 增强观测版
    """
    engine = SpineEngine()
    doc_path = "ceshi_ocr/tuimian.pdf"
    
    if not os.path.exists(doc_path):
        print(f"❌ [Audit] 找不到目标文件: {doc_path}")
        return

    print(f"\n🚀 [Audit] 启动增强型专项收割：{doc_path}")
    print(f"🛠️ [Audit] 关键观测点已激活：")
    print(f"   1. 采样颗粒度检测 (Buffer=1)")
    print(f"   2. Bitable AI 反哺字段提取验证")
    print(f"   3. 豆包 2.0 标签驱动聚类观测\n")

    try:
        # 🚀 临时劫持打印以增强可见性
        from backend.app.services.feishu.bitable_ledger import bitable_ledger
        
        # 使用 force=True 确保清除旧记录，触发完整新流水线
        result = await engine.ingest_document(doc_path, force=True)
        
        print("\n" + "🏁" * 20)
        print(f"✅ [Audit] 任务收官报告：")
        print(f"   - Bitable ID: {result.get('bitable_id')}")
        
        toc = result.get('toc', [])
        print(f"   - 合成脊梁项: {len(toc)}")
        for node in toc:
            source_tag = "[Doubao]" if node.source == "latent_distiller" else "[System]"
            print(f"     ↳ {source_tag} L{node.level} {node.title} (P{node.physical_start}-P{node.physical_end})")
        
        print("🏁" * 20)
        
    except Exception as e:
        print(f"\n❌ [Audit] 任务崩溃: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_exclusive_ingestion())
