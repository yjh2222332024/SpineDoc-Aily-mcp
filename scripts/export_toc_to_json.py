import asyncio
import sys
import json
from pathlib import Path
from uuid import UUID
from rich.console import Console

# 🏛️ 顶级架构锚定
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Document, TocItem
from sqlalchemy import select

console = Console()

class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        return super().default(obj)

async def export_toc():
    console.print("[bold cyan]💾 [Backup] 正在执行 TOC 脊梁物理备份...[/bold cyan]")
    session_maker = get_async_sessionmaker()
    
    async with session_maker() as session:
        # 1. 锁定 1.pdf
        stmt_doc = select(Document).where(Document.filename == '1.pdf').order_by(Document.created_at.desc()).limit(1)
        doc = (await session.execute(stmt_doc)).scalar_one_or_none()
        
        if not doc:
            console.print("[red]❌ 数据库中未找到 1.pdf 记录。[/red]")
            return

        # 2. 获取所有 TOC 项
        stmt_toc = select(TocItem).where(TocItem.document_id == doc.id).order_by(TocItem.physical_start)
        tocs = (await session.execute(stmt_toc)).scalars().all()
        
        # 3. 构造备份数据
        backup_data = {
            "document": {
                "id": str(doc.id),
                "filename": doc.filename,
                "total_pages": doc.total_pages,
                "page_offset": doc.page_offset
            },
            "spine_nodes": [
                {
                    "id": str(t.id),
                    "title": t.title,
                    "level": t.level,
                    "logical_page": t.page,
                    "physical_start": t.physical_start,
                    "physical_end": t.physical_end,
                    "parent_id": str(t.parent_id) if t.parent_id else None
                } for t in tocs
            ]
        }

        # 4. 物理写入
        output_path = PROJECT_ROOT / "ceshi_ocr" / "1.pdf.toc_spine.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2, cls=UUIDEncoder)
            
        console.print(f"[bold green]✅ [Success] TOC 备份已完成：{output_path}[/bold green]")
        console.print(f"📊 已归档 {len(tocs)} 个逻辑节点。")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(export_toc())
