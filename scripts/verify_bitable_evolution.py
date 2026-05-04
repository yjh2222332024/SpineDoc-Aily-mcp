import asyncio
import json
from backend.app.services.feishu.bitable_ledger import bitable_ledger

async def verify_evolution():
    print("🚀 [Verify] Searching for Evolved Knowledge in Bitable...")
    
    table_id = bitable_ledger.tables['chunks']['id']
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{bitable_ledger.app_token}/tables/{table_id}/records/search"
    
    # 搜索包含 "evolved" 的记录
    payload = {
        "filter": {
            "conjunction": "and",
            "conditions": [
                {"field_name": "Git版本", "operator": "contains", "value": ["evolved"]}
            ]
        },
        "page_size": 20
    }
    
    resp = await bitable_ledger._api_request("POST", url, json_data=payload)
    
    if resp.get("code") == 0:
        items = resp.get("data", {}).get("items", [])
        print(f"✅ Success! Found {len(items)} evolved records.")
        for it in items:
            f = it.get("fields", {})
            print(f"\n--- Evolved Chunk {it['record_id']} ---")
            print(f"   Content: {bitable_ledger._plain_text(f.get('正文内容'))[:100]}...")
            print(f"   Logic Summary: {bitable_ledger._plain_text(f.get('逻辑摘要'))}")
            print(f"   Galaxy Link: {f.get('星系关联')}")
    else:
        print(f"❌ Failed: {resp.get('msg')}")

if __name__ == "__main__":
    asyncio.run(verify_evolution())
