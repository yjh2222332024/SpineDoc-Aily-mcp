"""
SpineDoc Sovereignty Crusade: Full Ingestion Orchestrator (Industrial Grade)
===========================================================================
Responsibility:
1. Orchestrates the ingestion of the entire doc/ directory.
2. Ensures temporal logic (old to new).
3. Provides fault tolerance and detailed status tracking.
"""

import asyncio
import os
import hashlib
from pathlib import Path
from typing import List
from backend.app.services.spine_engine import SpineEngine

async def calculate_file_hash(path: Path) -> str:
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

async def main():
    print(" [Crusade] Starting Full Sovereignty Confirmation...")
    engine = SpineEngine()
    docs_dir = Path("docs")
    
    # 1. Catalog assets and sort by modification time (Historical Order)
    assets = list(docs_dir.glob("**/*.md")) + list(docs_dir.glob("**/*.pdf"))
    assets.sort(key=lambda x: x.stat().st_mtime)
    
    print(f" Found {len(assets)} physical assets. Beginning ingestion...")

    results = {"success": 0, "fail": 0, "skipped": 0}
    
    for i, asset in enumerate(assets):
        print(f"\n [{i+1}/{len(assets)}] Processing: {asset.name}")
        try:
            file_hash = await calculate_file_hash(asset)
            
            #  Execute Atomic Ingestion
            result = await engine.ingest(
                str(asset), 
                file_hash=file_hash,
                tag_timeout=600 # 给云端打标留足时间
            )
            
            if result.get("bitable_id"):
                print(f" Success: {asset.name} (Bitable: {result['bitable_id']})")
                results["success"] += 1
            else:
                print(f" Warning: {asset.name} completed but ID is None (possibly skipped?)")
                results["skipped"] += 1
                
        except Exception as e:
            print(f" Failed: {asset.name} | Error: {e}")
            results["fail"] += 1
            
        #  Defensive Interval: Let the cloud breathe
        await asyncio.sleep(2)

    print("\n" + "="*50)
    print("🏁 [Crusade] Campaign Concluded.")
    print(f"📊 Results: Success {results['success']} | Fail {results['fail']} | Skipped {results['skipped']}")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
