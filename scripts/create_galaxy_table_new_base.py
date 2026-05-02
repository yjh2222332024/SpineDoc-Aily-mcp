
import asyncio
import httpx
import os
import json
from dotenv import load_dotenv

async def create_galaxy_table():
    load_dotenv(override=True)
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    base_token = "QYcPbqEtRauhufslFwtc3sRenrc" # Our new Sovereign Base

    print(f"🚀 [Setup] 正在获取飞书令牌...")
    async with httpx.AsyncClient() as client:
        resp = await client.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", 
                               json={"app_id": app_id, "app_secret": app_secret})
        token = resp.json().get("tenant_access_token")
        headers = {"Authorization": f"Bearer {token}"}

        # Create Table
        create_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables"
        payload = {
            "table": {
                "name": "逻辑星系_Galaxies"
            }
        }
        resp = await client.post(create_url, json=payload, headers=headers)
        table_data = resp.json()
        if table_data.get("code") != 0:
            print(f"❌ [Setup] 创建表格失败: {table_data}")
            return

        table_id = table_data["data"]["table_id"]
        print(f"✅ [Setup] 成功创建星系表! ID: {table_id}")

        # Create Fields
        fields_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/fields"
        fields = [
            {"field_name": "星系名称", "type": 1},
            {"field_name": "锚点关键词", "type": 1},
            {"field_name": "逻辑聚类ID", "type": 1},
            {"field_name": "成员总数", "type": 2},
            {"field_name": "描述", "type": 1}
        ]

        for f in fields:
            f_resp = await client.post(fields_url, json=f, headers=headers)
            print(f"   ↳ 字段 '{f['field_name']}': {f_resp.json().get('msg')}")

        print("\n" + "⭐" * 30)
        print(f"新主权基地 Base Token: {base_token}")
        print(f"FEISHU_BITABLE_GALAXY_TABLE_ID={table_id}")
        print("⭐" * 30)

if __name__ == "__main__":
    asyncio.run(create_galaxy_table())
