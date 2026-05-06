import asyncio
import json
from backend.app.services.feishu.bitable_ledger import bitable_ledger

async def test_field_id_filter():
    # 星系关联的 Field ID 是 fldoDq3kRI
    # 番茄炒蛋星系的 Record ID 是 recvisQmRUTH2e
    table_id = bitable_ledger.tables['chunks']['id']
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{bitable_ledger.app_token}/tables/{table_id}/records/search"
    
    payload = {
        "filter": {
            "conjunction": "and",
            "conditions": [
                {"field_name": "fldoDq3kRI", "operator": "contains", "value": ["recvisQmRUTH2e"]}
            ]
        },
        "page_size": 20
    }
    
    print(f" [Probe] Testing Field ID filter for Galaxy Link...")
    resp = await bitable_ledger._api_request("POST", url, json_data=payload)
    
    if resp.get("code") == 0:
        items = resp.get("data", {}).get("items", [])
        print(f" Success! Found {len(items)} chunks linked to the Galaxy.")
        for it in items:
            print(f"   - Chunk {it['record_id']} | Text: {bitable_ledger._plain_text(it['fields'].get('正文内容'))[:30]}...")
    else:
        print(f" Failed: {resp.get('msg')}")

if __name__ == "__main__":
    asyncio.run(test_field_id_filter())
