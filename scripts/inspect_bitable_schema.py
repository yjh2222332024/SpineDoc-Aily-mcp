import asyncio
import json
from pathlib import Path
from backend.app.core.config import settings
from backend.app.services.feishu.bitable_ledger import bitable_ledger

async def inspect_schema():
    base_token = settings.FEISHU_BITABLE_TOKEN
    print(f" 正在检查多维表格: {base_token}")

    for table_key, table_info in bitable_ledger.tables.items():
        table_id = table_info["id"]
        if not table_id:
            print(f"\n--- 表: {table_key} (未配置) ---")
            continue
        print(f"\n--- 表: {table_key} (ID: {table_id}) ---")

        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/fields"
        try:
            resp = await bitable_ledger._api_request("GET", url)
            if resp.get("code") != 0:
                print(f" 无法读取表 {table_key}: {resp.get('msg')}")
                continue

            items = resp.get("data", {}).get("items", [])
            actual_fields = {it["field_name"]: it["field_id"] for it in items}

            for logical_name in table_info.get("fields", {}):
                target_display_name = logical_name  # 直接使用 display name
                found_id = actual_fields.get(target_display_name)

                if found_id:
                    print(f"  {logical_name}: {found_id}")
                else:
                    print(f"  {logical_name}:  未在云端找到该命名的字段")
                    print(f"    [云端现有]: {list(actual_fields.keys())}")
        except Exception as e:
            print(f" 检查出错: {str(e)}")

if __name__ == "__main__":
    asyncio.run(inspect_schema())
