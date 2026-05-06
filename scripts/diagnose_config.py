
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from backend.app.core.config import settings

import os

def diagnose_config():
    print(f" [Diagnosis] LLM Provider: {settings.LLM_PROVIDER}")
    print(f" [Diagnosis] LLM Base URL: {settings.LLM_BASE_URL}")
    
    # 检查 Bitable 座标
    print(f"\n📊 [Bitable] App ID: {os.getenv('FEISHU_APP_ID')[:8]}...")
    print(f"📊 [Bitable] Table Docs: {os.getenv('FEISHU_BITABLE_TABLE_ID')}")
    print(f"📊 [Bitable] Table Chunks: {os.getenv('FEISHU_BITABLE_CHUNK_TABLE_ID')}")
    print(f"📊 [Bitable] Table TOC: {os.getenv('FEISHU_BITABLE_TOC_TABLE_ID')}")
    
    # 检查 Pydantic 加载后的结果
    print(f"\n [Pydantic] LLM_API_KEY: {settings.LLM_API_KEY[:4] if settings.LLM_API_KEY else 'MISSING'}...")
    print(f" [Pydantic] LLM_ENDPOINT: {settings.LLM_ENDPOINT}")
    
    # 检查 OS 原始变量
    llm_key_raw = os.getenv("LLM_API_KEY")
    llm_ep_raw = os.getenv("LLM_ENDPOINT")
    print(f" [OS-Raw] LLM_API_KEY (raw): {llm_key_raw[:4] if llm_key_raw else 'NOT_IN_OS'}...")
    print(f" [OS-Raw] LLM_ENDPOINT (raw): {llm_ep_raw if llm_ep_raw else 'NOT_IN_OS'}")
    
    print(f" [Final] >>> REAL_LLM_KEY: {settings.REAL_LLM_KEY[:4] if settings.REAL_LLM_KEY else 'MISSING'}...")
    print(f" [Final] >>> REAL_LLM_MODEL: {settings.REAL_LLM_MODEL}")

if __name__ == "__main__":
    diagnose_config()
