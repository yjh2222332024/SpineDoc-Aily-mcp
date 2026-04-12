"""
检查 1.pdf 的关键词和摘要质量
"""

import asyncio
import sys
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.core.db import get_async_sessionmaker
from sqlmodel import select
from app.core.models import Document, TocItem, Chunk

async def inspect_chinese_quality():
    session_maker = get_async_sessionmaker()
    
    async with session_maker() as session:
        # 1. 查找 1.pdf 文档
        stmt = select(Document).where(Document.filename == "1.pdf")
        docs = (await session.execute(stmt)).scalars().all()
        
        if not docs:
            print("❌ 数据库中没有 1.pdf")
            return
        
        doc = docs[0]
        print("=" * 80)
        print(f"📄 文档：{doc.filename}")
        print("=" * 80)
        
        # 2. 获取所有 Chunk
        stmt = select(Chunk).where(Chunk.document_id == doc.id)
        chunks = (await session.execute(stmt)).scalars().all()
        
        print(f"\n📦 Chunk 总数：{len(chunks)}")
        
        # 3. 检查关键词和摘要格式
        print(f"\n🔍 格式检查:")
        
        chunks_with_keywords = 0
        chunks_with_summary = 0
        chunks_with_structure = 0
        empty_keywords = 0
        empty_summary = 0
        
        for c in chunks:
            if "【关键词:" in c.content:
                chunks_with_keywords += 1
                # 检查是否为空
                kw_match = re.search(r'【关键词：(.*?)】', c.content)
                if kw_match and kw_match.group(1).strip() in ['', 'N/A']:
                    empty_keywords += 1
            else:
                empty_keywords += 1
            
            if "【本章核心精要:" in c.content:
                chunks_with_summary += 1
                # 检查是否为空
                sum_match = re.search(r'【本章核心精要：(.*?)】', c.content)
                if sum_match and sum_match.group(1).strip() in ['', 'N/A']:
                    empty_summary += 1
            else:
                empty_summary += 1
            
            if "[STRUCTURE:" in c.content:
                chunks_with_structure += 1
        
        print(f"   有关键词：{chunks_with_keywords}/{len(chunks)} ({chunks_with_keywords/len(chunks)*100:.1f}%)")
        print(f"   空关键词：{empty_keywords}/{len(chunks)} ({empty_keywords/len(chunks)*100:.1f}%)")
        print(f"   有摘要：{chunks_with_summary}/{len(chunks)} ({chunks_with_summary/len(chunks)*100:.1f}%)")
        print(f"   空摘要：{empty_summary}/{len(chunks)} ({empty_summary/len(chunks)*100:.1f}%)")
        print(f"   有结构：{chunks_with_structure}/{len(chunks)} ({chunks_with_structure/len(chunks)*100:.1f}%)")
        
        # 4. 抽样显示关键词和摘要
        print(f"\n📝 关键词和摘要抽样 (前 20 个):")
        
        for i, c in enumerate(chunks[:20]):
            print(f"\n   [{i+1}] P{c.page_number} - {c.breadcrumb[:50]}...")
            
            # 提取关键词（修复正则）
            kw_match = re.search(r'【关键词：\s*(.*?)\s*】', c.content)
            keywords = kw_match.group(1) if kw_match else "❌ 未找到"
            print(f"       关键词：{keywords}")
            
            # 提取摘要（修复正则）
            sum_match = re.search(r'【本章核心精要：\s*(.*?)\s*】', c.content)
            summary = sum_match.group(1) if sum_match else "❌ 未找到"
            print(f"       摘要：{summary}")
            
            # 内容预览
            content_match = re.search(r'\[STRUCTURE:.*?\](.*?)(?=\n\n|$)', c.content, re.DOTALL)
            content_preview = content_match.group(1).strip()[:100] if content_match else "N/A"
            print(f"       内容预览：{content_preview}...")
        
        # 5. 质量评估
        print(f"\n🎯 质量评估:")
        
        # 关键词质量
        good_keywords = 0
        bad_keywords = 0
        for c in chunks[:50]:  # 抽样前 50 个
            kw_match = re.search(r'【关键词：(.*?)】', c.content)
            if kw_match:
                kw = kw_match.group(1)
                # 检查是否有实际内容
                if kw.strip() and kw.strip() != 'N/A':
                    # 检查是否有中文关键词
                    if any('\u4e00' <= ch <= '\u9fff' for ch in kw):
                        good_keywords += 1
                    else:
                        bad_keywords += 1
                else:
                    bad_keywords += 1
            else:
                bad_keywords += 1
        
        print(f"   有效关键词：{good_keywords}/{min(50, len(chunks))} ({good_keywords/min(50, len(chunks))*100:.1f}%)")
        print(f"   无效关键词：{bad_keywords}/{min(50, len(chunks))} ({bad_keywords/min(50, len(chunks))*100:.1f}%)")
        
        # 摘要质量
        good_summary = 0
        bad_summary = 0
        for c in chunks[:50]:  # 抽样前 50 个
            sum_match = re.search(r'【本章核心精要：(.*?)】', c.content)
            if sum_match:
                summary = sum_match.group(1)
                # 检查是否有实际内容
                if summary.strip() and summary.strip() != 'N/A' and '本章无具体内容' not in summary:
                    good_summary += 1
                else:
                    bad_summary += 1
            else:
                bad_summary += 1
        
        print(f"   有效摘要：{good_summary}/{min(50, len(chunks))} ({good_summary/min(50, len(chunks))*100:.1f}%)")
        print(f"   无效摘要：{bad_summary}/{min(50, len(chunks))} ({bad_summary/min(50, len(chunks))*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(inspect_chinese_quality())
