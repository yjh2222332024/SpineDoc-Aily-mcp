import asyncio
import hashlib
from pathlib import Path
from backend.app.services.spine_engine import SpineEngine

async def calculate_file_hash(path: Path) -> str:
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

async def test_ingest():
    file_path = "docs/1.md"
    print(f"🚀 [Test] Starting re-engineered ingestion for: {file_path}")
    
    engine = SpineEngine()
    file_hash = await calculate_file_hash(Path(file_path))
    
    # 执行确权入库
    # tag_timeout 设为 600 秒，给 Bitable AI 留足孵化时间
    result = await engine.ingest(file_path, file_hash=file_hash, tag_timeout=600, force=True)
    
    print("\n" + "="*50)
    print(f"🏁 [Test] Ingestion Result: {result.get('bitable_id', 'FAILED')}")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(test_ingest())
