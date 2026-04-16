import asyncio
import sys
from pathlib import Path

# 🏛️ 顶级架构锚定
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.app.services.spine_engine import SpineEngine

async def restore_spine_only():
    engine = SpineEngine()
    # 使用绝对路径确保不出错
    test_pdf = PROJECT_ROOT / "ceshi_ocr" / "1.pdf"
    
    print(f"🚀 [Restore] 正在恢复 {test_pdf.name} 的逻辑脊梁 (TOC Only)...")
    
    try:
        # 🏛️ 极致克制模式：force=False, force_ocr=False
        # 这将触发系统的自愈逻辑：如果 TOC 没了就补 TOC
        await engine.ingest_document(
            file_path=str(test_pdf.absolute()),
            force=False,         # 严禁删除旧记录
            force_ocr=False,     # 严禁重跑 OCR
            manual_toc_range=[9, 15],
            manual_offset=17,
            limit_pages=20,       # 仅运行前几页以触发 TOC 逻辑
          
        )
        print("\n[bold green]✅ 脊梁复活完成！数据库中的 TOC 树已对齐。[/bold green]")
    except Exception as e:
        print(f"🚨 恢复失败: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(restore_spine_only())
