"""
SpineDoc Ingest 调试脚本
用于诊断 ingest_document 流程中的具体问题
"""

import asyncio
import sys
from pathlib import Path

# 路径配置
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from spine_cli.core.engine import SpineEngine
from app.services.parser import hybrid_parser
from app.services.toc.aligner import LogicAligner
from app.services.rag.splitter import context_splitter
import fitz

async def debug_ingest():
    engine = SpineEngine()
    file_path = r"E:\study\code\SpineDoc\Spine-open\ocr_ceshi\1.pdf"
    
    print("=" * 80)
    print("🔍 SpineDoc Ingest 诊断程序")
    print("=" * 80)
    
    # 检查文件是否存在
    if not Path(file_path).exists():
        print(f"❌ 文件不存在：{file_path}")
        return
    
    print(f"\n📄 目标文件：{file_path}")
    print(f"📊 文件大小：{Path(file_path).stat().st_size / 1024 / 1024:.2f} MB")
    
    # 检查 PDF 总页数
    doc = fitz.open(file_path)
    total_pages = len(doc)
    print(f"📖 总页数：{total_pages}")
    doc.close()
    
    # ========== 测试 1: TOC 提取 ==========
    print("\n" + "=" * 80)
    print("测试 1: TOC 提取")
    print("=" * 80)
    
    manual_range = [9, 10, 11, 12, 13, 14, 15]
    print(f"手动指定目录范围：{manual_range}")
    
    try:
        toc = await hybrid_parser.extract_toc_async(file_path, manual_range=manual_range)
        print(f"✅ TOC 提取成功，数量：{len(toc)}")
        
        if toc:
            print("\n前 5 个 TOC 项:")
            for i, item in enumerate(toc[:5]):
                print(f"  [{i}] {item}")
        else:
            print("⚠️ TOC 为空！")
            
    except Exception as e:
        print(f"❌ TOC 提取失败：{e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========== 测试 2: 偏移计算 ==========
    print("\n" + "=" * 80)
    print("测试 2: 偏移计算与 TOC 对齐")
    print("=" * 80)
    
    try:
        offset = LogicAligner.calculate_offset(toc)
        print(f"计算偏移量：{offset}")
        
        enriched_toc = LogicAligner.align_toc(toc, offset)
        print(f"对齐后 TOC 数量：{len(enriched_toc)}")
        
        if enriched_toc:
            print("\n前 5 个对齐后的 TOC 项:")
            for i, item in enumerate(enriched_toc[:5]):
                print(f"  [{i}] {item}")
        
        is_scanned = LogicAligner.detect_is_scanned(toc)
        print(f"\n检测结果：is_scanned={is_scanned}")
        
    except Exception as e:
        print(f"❌ 偏移计算失败：{e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========== 测试 3: OCR 数字化 ==========
    print("\n" + "=" * 80)
    print("测试 3: OCR 数字化")
    print("=" * 80)
    
    page_markdowns = {}
    
    try:
        if is_scanned:
            print("检测到扫描件，执行全量 OCR...")
            from app.services.ocr.body_alchemist import BodyAlchemist
            alchemist = BodyAlchemist(concurrent_limit=8)
            enriched_toc, page_markdowns = await alchemist.run_full_pipeline(
                file_path, enriched_toc, total_pages, limit_pages=None
            )
        else:
            print("检测到文本 PDF，执行快速提取...")
            with fitz.open(file_path) as doc:
                temp_chunks = context_splitter.split_by_toc(doc, enriched_toc, layout_profile=hybrid_parser.layout_profile)
                pages_to_patch = {c["page_number"] for c in temp_chunks if "[COMPLEX_STRUCTURE_DETECTED]" in c["content"]}
                
                if pages_to_patch:
                    print(f"发现 {len(pages_to_patch)} 个复杂页面，需要 OCR 补丁")
                    target_indices = [idx - 1 for idx in pages_to_patch if 0 < idx <= total_pages]
                    from app.services.ocr.body_alchemist import BodyAlchemist
                    alchemist = BodyAlchemist(concurrent_limit=8)
                    page_markdowns = await alchemist.harvest_pages(file_path, target_pages=target_indices)
                else:
                    print("无需 OCR 补丁")
        
        print(f"✅ OCR 完成，获取 {len(page_markdowns)} 页 Markdown")
        if page_markdowns:
            print(f"   页码范围：{min(page_markdowns.keys())+1} - {max(page_markdowns.keys())+1}")
            
    except Exception as e:
        print(f"❌ OCR 失败：{e}")
        import traceback
        traceback.print_exc()
        # 继续执行，测试是否能跳过 OCR
    
    # ========== 测试 4: 语义切片 ==========
    print("\n" + "=" * 80)
    print("测试 4: 语义切片")
    print("=" * 80)
    
    try:
        print(f"准备切片参数:")
        print(f"  - enriched_toc: {len(enriched_toc)} 项")
        print(f"  - page_markdowns: {len(page_markdowns)} 页")
        print(f"  - layout_profile: {hybrid_parser.layout_profile}")
        
        with fitz.open(file_path) as doc:
            chunks = context_splitter.split_by_toc(
                doc, 
                enriched_toc, 
                ocr_context=page_markdowns, 
                layout_profile=hybrid_parser.layout_profile
            )
        
        print(f"✅ 语义切片成功，生成 {len(chunks)} 个 Chunk")
        
        if chunks:
            print("\n前 3 个 Chunk:")
            for i, c in enumerate(chunks[:3]):
                print(f"  [{i}] page={c.get('page_number')}, breadcrumb={c.get('breadcrumb', 'N/A')}, content_len={len(c.get('content', ''))}")
                
    except Exception as e:
        print(f"❌ 语义切片失败：{e}")
        import traceback
        traceback.print_exc()
        return
    
    # ========== 测试 5: 数据库写入 ==========
    print("\n" + "=" * 80)
    print("测试 5: 数据库写入")
    print("=" * 80)
    
    from uuid import UUID, uuid4
    from app.core.models import Document, TocItem, Chunk, ProcessingStatus
    from app.core.db import get_async_sessionmaker
    
    session_maker = get_async_sessionmaker()
    file_hash = engine._calculate_file_hash(file_path)
    
    try:
        async with session_maker() as session:
            # 1. 插入 Document
            print("1. 插入 Document...")
            db_doc = Document(
                id=uuid4(),
                filename=Path(file_path).name,
                file_path=str(file_path),
                file_hash=file_hash,
                status=ProcessingStatus.COMPLETED,
                total_pages=total_pages,
                is_scanned=is_scanned,
                page_offset=offset
            )
            session.add(db_doc)
            await session.commit()
            await session.refresh(db_doc)
            doc_id = str(db_doc.id)
            print(f"   ✅ Document 插入成功，id={doc_id}")
            
            # 2. 插入 TocItem
            print("2. 插入 TocItem...")
            db_tocs = []
            for i, it in enumerate(enriched_toc):
                try:
                    toc_id = UUID(it["id"]) if "id" in it else uuid4()
                    db_tocs.append(TocItem(
                        id=toc_id,
                        title=it.get("title", f"Untitled_{i}"),
                        page=it.get("page", 0),
                        level=it.get("level", 1),
                        document_id=db_doc.id,
                        physical_start=it.get("page", 0)
                    ))
                except Exception as e:
                    print(f"   ⚠️ TOC 项 {i} 转换失败：{e}, 数据：{it}")
                    raise
            
            session.add_all(db_tocs)
            await session.flush()
            print(f"   ✅ TocItem 插入成功，数量={len(db_tocs)}")
            
            # 3. 插入 Chunk
            print("3. 插入 Chunk...")
            db_chunks = []
            for i, c in enumerate(chunks):
                try:
                    chunk_id = UUID(c.get("id", str(uuid4())))
                    db_chunks.append(Chunk(
                        id=chunk_id,
                        content=c.get("content", ""),
                        page_number=c.get("page_number", 0),
                        breadcrumb=c.get("breadcrumb", ""),
                        document_id=db_doc.id,
                        metadata_json=c.get("metadata_json", {})
                    ))
                except Exception as e:
                    print(f"   ⚠️ Chunk {i} 转换失败：{e}, 数据：{c}")
                    raise
            
            session.add_all(db_chunks)
            await session.flush()
            print(f"   ✅ Chunk 插入成功，数量={len(db_chunks)}")
            
            # 4. 提交
            print("4. 提交事务...")
            await session.commit()
            print(f"   ✅ 数据库写入完成！")
            
        print(f"\n🎉 完整 Ingest 流程测试成功！")
        print(f"   doc_id={doc_id}")
        
    except Exception as e:
        print(f"❌ 数据库写入失败：{e}")
        import traceback
        traceback.print_exc()
        
        # 尝试回滚
        print("\n尝试清理残留数据...")
        try:
            async with session_maker() as session:
                if 'db_doc' in locals():
                    from sqlmodel import delete
                    await session.execute(delete(Chunk).where(Chunk.document_id == db_doc.id))
                    await session.execute(delete(TocItem).where(TocItem.document_id == db_doc.id))
                    await session.execute(delete(Document).where(Document.id == db_doc.id))
                    await session.commit()
                    print("✅ 已清理残留数据")
        except:
            print("⚠️ 清理失败，请手动检查数据库")

if __name__ == "__main__":
    asyncio.run(debug_ingest())
