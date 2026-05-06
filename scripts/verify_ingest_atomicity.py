import asyncio
from pathlib import Path
from backend.app.services.orchestrators.ingestion_service import DocumentIngestionService
from backend.app.services.ocr.body_alchemist import PdfTextExtractor
from backend.app.services.feishu.bitable_ledger import bitable_ledger

async def verify_atomic_ingest():
    print(" [Verification] 开启单点入库原子测试...")
    alchemist = PdfTextExtractor()
    ingestion_service = DocumentIngestionService(alchemist, store=bitable_ledger)
    f = Path("docs/20260409_dev_log.md")
    
    try:
        print(f" 正在强制入库: {f.name}")
        result = await ingestion_service.ingest(file_path=str(f), force=True)
        print(f" 原子入库验证成功! Bitable ID: {result.get('bitable_id')}")
        return True
    except Exception as e:
        print(f" 严重错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(verify_atomic_ingest())
