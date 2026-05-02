import asyncio
import os
import sys
from pathlib import Path

# 确权环境
sys.path.append(os.getcwd())

from backend.app.services.orchestrators.structured_text import StructuredTextOrchestrator
from backend.app.services.feishu.bitable_ledger import bitable_ledger

async def verify_single_doc():
    print("🛡️ [Verification] 开启单文档确权验证 (Direct Orchestrator Mode)...")
    target_file = "docs/20260424_milestone_convergence_log.md"
    
    if not Path(target_file).exists():
        print(f"❌ 找不到目标文件: {target_file}")
        return

    # 直接实例化具体的编排器
    orchestrator = StructuredTextOrchestrator(store=bitable_ledger)
    
    # 模拟 SpineEngine (如果需要)
    from unittest.mock import MagicMock
    mock_engine = MagicMock()

    print(f"📄 正在对 {target_file} 执行物理切片与云端确权...")
    try:
        # 手动计算 hash 以匹配接口契约
        import hashlib
        with open(target_file, "rb") as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

        result = await orchestrator.ingest(
            file_path=target_file,
            file_hash=file_hash,
            engine=mock_engine,
            ctx=None
        )
        print(f"\n✅ 确权流程执行完毕！")
        print(f"📍 Bitable ID: {result.get('bitable_id')}")
        
    except Exception as e:
        print(f"❌ 流程中断: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_single_doc())
