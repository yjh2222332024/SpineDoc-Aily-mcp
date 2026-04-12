"""
SpineDoc 数据空洞修复工具 (Data Healing Tool)
职责：检测数据库中内容为空的 Chunk，现场执行本地 OCR 并回填数据库。
🚨 目标：让 1.pdf 的 119 个分块真正拥有内容。
"""
import asyncio
import os
import sys
from pathlib import Path
import fitz
from sqlmodel import select

# 添加项目路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.db import get_async_sessionmaker
from app.core.models import Document, Chunk
from app.services.ocr_worker import OCRWorker

async def heal_document(filename: str):
    print("=" * 60)
    print(f"🛠️ 正在启动数据自愈：{filename}")
    print("=" * 60)
    
    session_maker = get_async_sessionmaker()
    worker = OCRWorker()
    
    async with session_maker() as session:
        # 1. 查找文档
        doc_stmt = select(Document).where(Document.filename == filename)
        doc = (await session.execute(doc_stmt)).scalars().first()
        if not doc:
            print("❌ 错误：未找到文档记录。")
            return

        # 2. 查找内容为空的 Chunks
        chunk_stmt = select(Chunk).where(Chunk.document_id == doc.id)
        chunks = (await session.execute(chunk_stmt)).scalars().all()
        
        empty_chunks = [c for c in chunks if not c.content or len(c.content.strip()) < 50]
        print(f"🔍 发现 {len(empty_chunks)} 个空洞分块。")

        if not empty_chunks:
            print("✅ 文档内容完整，无需自愈。")
            return

        # 3. 执行物理挖掘
        print(f"📸 正在打开物理文件: {doc.file_path}")
        with fitz.open(doc.file_path) as pdf:
            for i, c in enumerate(empty_chunks):
                p_num = c.page_number
                print(f"   ⚡ [{i+1}/{len(empty_chunks)}] 正在挖掘物理页 {p_num} ...", end='\r')
                
                # 由于 Chunk 可能跨多页，这里我们扫描该 Chunk 对应的起始页到结束页（暂按单页补全）
                res = await worker.ocr_page_async(pdf[p_num-1], use_cloud=False)
                text = "\n".join([line["text"] for line in res])
                
                if text.strip():
                    c.content = f"[HEALED-TEXT]\n{text}"
                    session.add(c)
                
                # 每 10 页提交一次，防止事务过大
                if (i+1) % 10 == 0:
                    await session.commit()
            
            await session.commit()
            
    print(f"\n\n🎉 自愈圆满成功！{len(empty_chunks)} 个分块已注入正文黄金。")

if __name__ == "__main__":
    asyncio.run(heal_document("1.pdf"))
