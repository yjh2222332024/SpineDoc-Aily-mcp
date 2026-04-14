import asyncio
import sys
import time
from pathlib import Path
from uuid import UUID

# 🏛️ 顶级架构锚定
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from spine_cli.core.engine import SpineEngine
from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, Chunk, TocItem, ProcessingStatus
from sqlalchemy import select

async def run_v48_audit():
    print("🎬 [V48-Audit] 启动三段式守护者架构验证 (Manual Params)...")
    
    test_pdf = PROJECT_ROOT / "ceshi_ocr" / "1.pdf"
    if not test_pdf.exists():
        print(f"❌ [Error] 目标 PDF 不存在: {test_pdf}")
        return

    engine = SpineEngine()
    
    # 🎯 用户指定的确权参数
    manual_toc_range = [9, 15] 
    manual_offset = 17 

    print(f"🚀 [Pipeline] 开始处理文档...")
    print(f"📍 TOC Range: {manual_toc_range} | Manual Offset: {manual_offset}")

    start_time = time.time()
    try:
        # 🏛️ 调用引擎，传入确权参数
        result = await engine.ingest_document(
            file_path=str(test_pdf.absolute()),
            force=False, 
            force_ocr=True,
            manual_toc_range=manual_toc_range,
            manual_offset=manual_offset, # 🚀 V48.0 新参数
            limit_pages=None, 
            dev_mode=True
        )
        print(f"✅ [Pipeline] 执行成功，总耗时: {time.time()-start_time:.2f}s")
    except Exception as e:
        print(f"❌ [Pipeline] 崩溃: {e}")
        import traceback
        traceback.print_exc()
        return

    # 🔍 数据层法医核验
    print("\n🔍 [Forensic] 正在核验 V48.0 逻辑补全效果...")
    session_maker = get_async_sessionmaker()
    async with session_maker() as session:
        doc_id = UUID(result["id"])
        
        # 1. 验证 TOC 守护节点
        stmt_toc = select(TocItem).where(TocItem.document_id == doc_id).order_by(TocItem.physical_start)
        tocs = (await session.execute(stmt_toc)).scalars().all()
        
        print("\n🌳 脊梁拓扑审计 (验证 Level 1 并列守护者):")
        for t in tocs:
            is_intro = t.title == "[Introductory Material]"
            tag = "🛡️ [Guardian]" if is_intro else "📄 [Normal]"
            print(f"  {tag} L{t.level} | {t.title[:30]:<30} | P{t.physical_start}-P{t.physical_end}")

        # 2. 验证 Chunks 采样
        stmt_chunks = select(Chunk).where(Chunk.document_id == doc_id).order_by(Chunk.page_number)
        chunks = (await session.execute(stmt_chunks)).scalars().all()
        
        print(f"\n🧩 切片审计 (共 {len(chunks)} 个分片):")
        # 采样 P1 (Front Matter) 和 P16 (Preface)
        for c in chunks:
            if c.page_number in [1, 16]:
                print(f"\n📍 采样物理页 P{c.page_number} | Breadcrumb: {c.breadcrumb}")
                print(f"🏷️ Tags: {', '.join(c.logic_tags)}")
                print(f"📝 Content: {c.content[:200].replace('\n', ' ')}...")

    print("\n🏆 [Verdict] 验证结束。")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_v48_audit())
