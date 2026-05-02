import asyncio
from pathlib import Path
from backend.app.services.orchestrators.ingestion_service import DocumentIngestionService
from backend.app.services.ocr.body_alchemist import PdfTextExtractor
from backend.app.services.feishu.bitable_ledger import bitable_ledger

async def verify_single_doc():
    print("🛡️ [Verification] 开启单文档严谨性验证...")
    # 明确只针对这一篇
    target_file = "docs/20260424_milestone_convergence_log.md"
    
    alchemist = PdfTextExtractor()
    ingestion_service = DocumentIngestionService(alchemist, store=bitable_ledger)
    
    print(f"📄 正在对 {target_file} 执行原子入库...")
    try:
        result = await ingestion_service.ingest(
            file_path=target_file,
            force=True
        )
        print(f"✅ 入库完成。Bitable ID: {result.get('bitable_id')}")
        print("🔍 请检查 Bitable 中该文档是否关联了星系，并是否存在摘要节点。")
    except Exception as e:
        print(f"❌ 验证失败: {e}")

if __name__ == "__main__":
    asyncio.run(verify_single_doc())
