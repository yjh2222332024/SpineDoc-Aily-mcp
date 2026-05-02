
import asyncio
import os
import sys
from pathlib import Path

# 确保能找到 backend 模块
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.app.services.spine_engine import SpineEngine

async def run_ingestion():
    """
    SpineDoc 实战入库脚本
    针对推免 (Emergent) 与游戏乱象 (Standard) 两个样本进行新逻辑切分入库。
    """
    engine = SpineEngine()
    
    # 文档路径
    doc1 = "ceshi_ocr/tuimian.pdf"
    doc2 = "ceshi_ocr/游戏收费乱象研究与治理.pdf"
    
    # 1. 推免 (Emergent)
    if os.path.exists(doc1):
        print(f"\n🦴 [Ingest] 正在处理: {doc1} (预计路由至 Emergent 管道)")
        try:
            result1 = await engine.ingest_document(doc1, force=True)
            print(f"✅ [Ingest] {doc1} 处理完成。Bitable ID: {result1.get('bitable_id')}")
        except Exception as e:
            print(f"❌ [Ingest] {doc1} 失败: {e}")
    else:
        print(f"⚠️ [Ingest] 未找到文件: {doc1}")

    # 2. 游戏收费 (Standard)
    if os.path.exists(doc2):
        print(f"\n🦴 [Ingest] 正在处理: {doc2} (预计路由至 Standard 管道)")
        try:
            result2 = await engine.ingest_document(doc2, force=True)
            print(f"✅ [Ingest] {doc2} 处理完成。Bitable ID: {result2.get('bitable_id')}")
        except Exception as e:
            print(f"❌ [Ingest] {doc2} 失败: {e}")
    else:
        print(f"⚠️ [Ingest] 未找到文件: {doc2}")

if __name__ == "__main__":
    asyncio.run(run_ingestion())
