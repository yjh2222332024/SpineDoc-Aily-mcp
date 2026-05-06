import asyncio
import json
from backend.app.services.feishu.bitable_ledger import bitable_ledger

async def verify_tomato_chunks():
    doc_id = "recvisQaciYfIF" # 1.md 的 ID
    print(f" [Verify] Checking chunks for Document: {doc_id}")
    
    # 强制拉取该文档的所有分片
    table_id = bitable_ledger.tables['chunks']['id']
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{bitable_ledger.app_token}/tables/{table_id}/records/search"
    payload = {
        "filter": {
            "conjunction": "and",
            "conditions": [{"field_name": "文档关联", "operator": "is", "value": [doc_id]}]
        },
        "page_size": 20
    }
    
    resp = await bitable_ledger._api_request("POST", url, json_data=payload)
    items = resp.get("data", {}).get("items", [])
    
    print(f" Results: {len(items)} chunks found.")
    for it in items:
        f = it.get("fields", {})
        print(f"\n--- Chunk {it['record_id']} ---")
        print(f"   正文: {f.get('正文内容', '')[:50]}...")
        print(f"   星系关联: {f.get('星系关联')}")
        print(f"   Git版本: {f.get('Git版本')}")

if __name__ == "__main__":
    asyncio.run(verify_tomato_chunks())
