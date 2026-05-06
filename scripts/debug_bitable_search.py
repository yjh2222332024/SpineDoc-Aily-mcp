import asyncio
import json
from backend.app.services.feishu.bitable_ledger import bitable_ledger

async def debug_bitable():
    print(" [Debug] Inspecting Chunks table directly...")
    
    table_id = bitable_ledger.tables['chunks']['id']
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{bitable_ledger.app_token}/tables/{table_id}/records/search"
    
    # 尝试多种过滤方式
    tests = [
        {"name": "Empty Conditions", "payload": {"page_size": 10}},
        {"name": "Git版本 IS v2.0-cloud (List)", "payload": {"filter": {"conjunction": "and", "conditions": [{"field_name": "Git版本", "operator": "is", "value": ["v2.0-cloud"]}]}, "page_size": 10}},
        {"name": "Git版本 CONTAINS v2.0-cloud", "payload": {"filter": {"conjunction": "and", "conditions": [{"field_name": "Git版本", "operator": "contains", "value": ["v2.0-cloud"]}]}, "page_size": 10}},
    ]
    
    for t in tests:
        print(f"\n Testing: {t['name']}")
        resp = await bitable_ledger._api_request("POST", url, json_data=t['payload'])
        items = resp.get("data", {}).get("items", [])
        print(f"   ↳ Results: {len(items)}")
        if items:
            print(f"   ↳ First record fields: {list(items[0]['fields'].keys())}")
            print(f"   ↳ First record Galaxy Link: {items[0]['fields'].get('星系关联')}")

if __name__ == "__main__":
    asyncio.run(debug_bitable())
