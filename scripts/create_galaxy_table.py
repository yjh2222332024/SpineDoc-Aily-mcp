
import asyncio
import httpx
import os
from dotenv import load_dotenv

async def create_galaxy_table():
    load_dotenv(override=True)
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    wiki_node_id = "O3WDwZtqGiVETqkdFghcH78vnLd"

    print(f" [Setup] 正在获取飞书令牌...")
    async with httpx.AsyncClient() as client:
        # 1. Get Token
        resp = await client.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", 
                               json={"app_id": app_id, "app_secret": app_secret})
        token = resp.json().get("tenant_access_token")
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get Obj Token (Base Token)
        wiki_url = f"https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node?token={wiki_node_id}"
        resp = await client.get(wiki_url, headers=headers)
        base_token = resp.json()["data"]["node"]["obj_token"]
        print(f" [Setup] 找到多维表格 Base Token: {base_token}")

        # 3. Create Table
        create_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables"
        payload = {
            "table": {
                "name": "逻辑星系 (Galaxies)",
                "default_view_name": "星系大观"
            }
        }
        resp = await client.post(create_url, json=payload, headers=headers)
        table_data = resp.json()
        if table_data.get("code") != 0:
            print(f" [Setup] 创建表格失败: {table_data}")
            return

        table_id = table_data["data"]["table_id"]
        print(f" [Setup] 成功创建星系表! ID: {table_id}")

        # 4. Create Fields
        fields_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/fields"
        
        # 定义字段 (1: Text, 2: Number, 4: MultiSelect)
        # 注意：默认已经有一个 "多维表格" 字段，我们改名或新建
        fields = [
            {"field_name": "星系名称", "type": 1},
            {"field_name": "锚点关键词", "type": 1},
            {"field_name": "逻辑聚类ID", "type": 1},
            {"field_name": "成员总数", "type": 2},
            {"field_name": "描述", "type": 1}
        ]

        for f in fields:
            f_resp = await client.post(fields_url, json=f, headers=headers)
            if f_resp.json().get("code") == 0:
                print(f"   ↳ 字段创建成功: {f['field_name']}")
            else:
                print(f"    字段 '{f['field_name']}' 创建异常 (可能已存在): {f_resp.json().get('msg')}")

        print("\n" + "" * 30)
        print(f"请将以下配置添加到你的 .env 文件中：")
        print(f"FEISHU_BITABLE_GALAXY_TABLE_ID={table_id}")
        print("" * 30)

if __name__ == "__main__":
    asyncio.run(create_galaxy_table())
