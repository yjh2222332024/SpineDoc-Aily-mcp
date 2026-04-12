
import asyncio
import sys
from pathlib import Path

# 添加路径
current_dir = Path(__file__).parent.parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / "backend"))

from spine_cli.core.engine import SpineEngine

async def main():
    engine = SpineEngine()
    paper_dir = current_dir / "examples" / "academic_papers"
    papers = [
        "2401.14887v4.pdf",
        "2310.11511v1.pdf",
        "2403.10131v2.pdf",
        "2502.12342v1.pdf",
        "2505.14069v3.pdf"
    ]
    
    for paper in papers:
        path = paper_dir / paper
        if path.exists():
            print(f"🚀 Ingesting {paper}...")
            try:
                doc_id = await engine.ingest_document(str(path), progress_callback=print)
                print(f"✅ Success: {doc_id}")
            except Exception as e:
                print(f"❌ Failed {paper}: {e}")
        else:
            print(f"⚠️ Not found: {path}")

if __name__ == "__main__":
    asyncio.run(main())
