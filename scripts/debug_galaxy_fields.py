import asyncio
import json
from backend.app.services.feishu.bitable_ledger import bitable_ledger

async def debug_galaxy_fields():
    gal_id = "recvisQmRUTH2e"
    gal_table = bitable_ledger.tables['galaxies']['id']
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{bitable_ledger.app_token}/tables/{gal_table}/records/{gal_id}"
    
    print(f"🚀 [Debug] Reading Galaxy Record: {gal_id}")
    resp = await bitable_ledger._api_request("GET", url)
    
    if resp.get("code") == 0:
        fields = resp.get("data", {}).get("record", {}).get("fields", {})
        print(f"✅ Found {len(fields)} fields.")
        for k, v in fields.items():
            print(f"   - Key: [{k}] | Type: {type(v)} | Value: {str(v)[:50]}...")
    else:
        print(f"❌ Failed: {resp.get('msg')}")

if __name__ == "__main__":
    asyncio.run(debug_galaxy_fields())
