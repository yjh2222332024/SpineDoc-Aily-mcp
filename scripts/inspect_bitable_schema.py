import asyncio
import json
from pathlib import Path
from backend.app.services.feishu.bitable_ledger import bitable_ledger

async def inspect_schema():
    manifest_path = Path("backend/storage/bitable_schema_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    base_token = manifest["base_token"]
    print(f"🔍 正在检查多维表格: {base_token}")
    
    for table_key, table_info in manifest["tables"].items():
        table_id = table_info["id"]
        print(f"\n--- 表: {table_key} (ID: {table_id}) ---")
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/fields"
        try:
            resp = await bitable_ledger._api_request("GET", url)
            if resp.get("code") != 0:
                print(f"❌ 无法读取表 {table_key}: {resp.get('msg')}")
                continue
                
            items = resp.get("data", {}).get("items", [])
            # 建立 名字 -> ID 的映射
            actual_fields = {it["field_name"]: it["field_id"] for it in items}
            
            for logical_name, current_id in table_info["fields"].items():
                # 尝试通过名字匹配
                match_id = None
                # 这里定义一些常见的显示名称映射
                name_map = {
                    "name": "星系名称",
                    "centroid_embedding": "重心向量",
                    "anchor_keywords": "锚点关键词",
                    "member_count": "成员总数",
                    "description": "星系描述",
                    "galaxy_link": "所属星系"
                }
                
                target_display_name = name_map.get(logical_name, logical_name)
                found_id = actual_fields.get(target_display_name)
                
                if found_id:
                    status = "✅ 匹配" if found_id == current_id else f"⚠️ 变更 ({current_id} -> {found_id})"
                    print(f"  {logical_name} ({target_display_name}): {status}")
                else:
                    print(f"  {logical_name} ({target_display_name}): ❌ 未在云端找到该命名的字段")
                    # 打印云端实际存在的字段供参考
                    print(f"    [云端现有]: {list(actual_fields.keys())}")
        except Exception as e:
            print(f"❌ 检查出错: {str(e)}")

if __name__ == "__main__":
    asyncio.run(inspect_schema())
