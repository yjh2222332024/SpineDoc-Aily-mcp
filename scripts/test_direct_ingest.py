"""
直接测试 V29.2 Ingest - 绕过 spine 命令
"""

import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from spine_cli.core.engine import SpineEngine

async def test_ingest():
    engine = SpineEngine()
    file_path = r"E:\study\code\SpineDoc\Spine-open\ocr_ceshi\1.pdf"
    
    print("=" * 80)
    print("🧪 V29.2 直接 Ingest 测试")
    print("=" * 80)
    
    try:
        doc_id = await engine.ingest_document(
            file_path,
            manual_toc_range=[9, 10, 11, 12, 13, 14, 15],
            limit_pages=50,
            progress_callback=lambda m: print(f"  > {m}")
        )
        print(f"\n✅ Ingest 成功！doc_id={doc_id}")
        
        # 验证
        doc_data = await engine.get_document(doc_id)
        if doc_data:
            print(f"\n📊 文档信息:")
            print(f"  - 文件名：{doc_data.get('filename', 'N/A')}")
            print(f"  - 总页数：{doc_data.get('total_pages', 'N/A')}")
            print(f"  - TOC 数量：{len(doc_data.get('toc', []))}")
            print(f"  - is_scanned: {doc_data.get('is_scanned', 'N/A')}")
            print(f"  - page_offset: {doc_data.get('page_offset', 'N/A')}")
            
            # 检查 TOC
            toc = doc_data.get('toc', [])
            if toc:
                print(f"\n📋 TOC 抽样 (前 5 项):")
                for i, t in enumerate(toc[:5]):
                    print(f"  [{i+1}] {t.get('title', 'N/A')} - P{t.get('page', 'N/A')} (L{t.get('level', 'N/A')})")
            else:
                print(f"\n⚠️ 警告：TOC 为空！")
        else:
            print(f"\n⚠️ 警告：无法获取文档信息！")
        
    except Exception as e:
        print(f"\n❌ Ingest 失败：{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ingest())
