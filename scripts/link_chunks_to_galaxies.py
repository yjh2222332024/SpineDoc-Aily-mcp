
import asyncio
import httpx
import os
from dotenv import load_dotenv

async def link_chunks_to_galaxies():
    load_dotenv(override=True)
    app_id = os.getenv("FEISHU_APP_ID")
    app_secret = os.getenv("FEISHU_APP_SECRET")
    base_token = "OjlubGVa1a92wqsmp4McfRvRnzd"
    chunks_table_id = "tblgTgxUGTUykcU2"
    galaxies_table_id = "tblUNoT6tTIWZtcF"

    print(f"🚀 [Linker] 正在打通星系与分片的逻辑隧道...")
    async with httpx.AsyncClient() as client:
        # 1. 获取 Token
        resp = await client.post("https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal", 
                               json={"app_id": app_id, "app_secret": app_secret})
        token = resp.json().get("tenant_access_token")
        headers = {"Authorization": f"Bearer {token}"}

        # 2. 在 Chunks 表中创建关联字段 (Type 18: Single Link, Type 21: Multi Link)
        # 我们选择 Multi Link (21)，因为一个分片可能属于多个星系（逻辑重叠）
        fields_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables/{chunks_table_id}/fields"
        payload = {
            "field_name": "星系关联",
            "type": 21,
            "property": {
                "table_id": galaxies_table_id,
                "multiple": True
            }
        }
        
        resp = await client.post(fields_url, json=payload, headers=headers)
        data = resp.json()
        
        if data.get("code") == 0:
            field_id = data["data"]["field"]["field_id"]
            print(f"✅ [Linker] 关联成功！字段 ID: {field_id}")
        else:
            print(f"⚠️ [Linker] 字段创建可能已存在或失败: {data.get('msg')}")

if __name__ == "__main__":
    asyncio.run(link_chunks_to_galaxies())
