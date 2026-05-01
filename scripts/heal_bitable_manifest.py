import asyncio
import json
from pathlib import Path
from backend.app.services.feishu.bitable_ledger import bitable_ledger

# 定义 逻辑 Key -> 飞书显示名称 的绝对映射
SCHEMA_MAP = {
    "galaxies": {
        "name": "星系名称",
        "centroid_embedding": "重心向量",
        "anchor_keywords": "锚点关键词",
        "member_count": "成员总数",
        "description": "描述",
        "anchor_tag_cloud": "锚点标签云"
    },
    "chunks": {
        "content": "正文内容",
        "logic_summary": "逻辑摘要",
        "logic_tags": "语义标签",
        "logic_coord": "逻辑坐标",
        "file_hash_link": "文档关联",
        "galaxy_link": "星系关联",
        "fingerprint": "逻辑指纹"
    },
    "documents": {
        "filename": "文件名",
        "file_hash": "文件哈希",
        "status": "处理状态",
        "total_pages": "总页数"
    }
}

async def heal_manifest():
    manifest_path = Path("backend/storage/bitable_schema_manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    base_token = manifest["base_token"]
    
    print(f"🛠️ [Healer] 开始修复多维表格主权清单: {base_token}")
    
    for table_key, field_map in SCHEMA_MAP.items():
        if table_key not in manifest["tables"]:
            print(f"⚠️ 跳过表 {table_key} (manifest 中未定义 ID)")
            continue
            
        table_id = manifest["tables"][table_key]["id"]
        print(f"  - 正在同步表: {table_key} ({table_id})")
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{base_token}/tables/{table_id}/fields"
        resp = await bitable_ledger._api_request("GET", url)
        
        if resp.get("code") != 0:
            print(f"❌ 无法读取表 {table_key} 的字段信息: {resp.get('msg')}")
            continue
            
        actual_fields = {it["field_name"]: it["field_id"] for it in resp.get("data", {}).get("items", [])}
        
        # 更新 manifest 中的字段 ID
        new_fields = {}
        for logic_key, display_name in field_map.items():
            if display_name in actual_fields:
                new_fields[logic_key] = actual_fields[display_name]
                print(f"    ✅ {logic_key} -> {display_name} (ID: {actual_fields[display_name]})")
            else:
                print(f"    ❌ 找不到字段: {display_name} (已忽略)")
        
        manifest["tables"][table_key]["fields"] = new_fields

    # 物理落盘
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n🎉 [Healer] 主权清单已修复并同步至物理文件。")

if __name__ == "__main__":
    asyncio.run(heal_manifest())
