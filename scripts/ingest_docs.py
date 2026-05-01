import asyncio
import os
import logging
from pathlib import Path
from backend.app.services.orchestrators.ingestion_service import DocumentIngestionService
from backend.app.services.ocr.body_alchemist import PdfTextExtractor
from backend.app.services.feishu.bitable_ledger import bitable_ledger

async def ingest_single_file(ingestion_service, f):
    print(f"\n📄 正在确权文件: {f.name}")
    try:
        # 执行确权
        result = await ingestion_service.ingest(
            file_path=str(f),
            force=True
        )
        print(f"✅ {f.name} 确权成功！Bitable ID: {result.get('bitable_id', 'Unknown')}")
        return result
    except Exception as e:
        print(f"❌ {f.name} 确权失败: {e}")
        return None

async def main():
    print("🛡️ [IngestCommand] 圣殿重建工程启动 (并行加速版)...")
    
    # 手动初始化服务
    alchemist = PdfTextExtractor()
    ingestion_service = DocumentIngestionService(alchemist, store=bitable_ledger)
    
    docs_dir = Path("docs")
    # 🚀 [V100.0] 全量确权模式开启
    files = [f for f in docs_dir.glob("*.md") if "work_log" not in f.name]
    
    batch_size = 3
    print(f"📦 发现 {len(files)} 个待确权文件，采用每批 {batch_size} 个并行处理。")
    
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        print(f"\n🚀 正在启动批次 {i//batch_size + 1}...")
        tasks = [ingest_single_file(ingestion_service, f) for f in batch]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    # 设置环境变量，确保能找到模块
    os.environ["PYTHONPATH"] = "."
    asyncio.run(main())
