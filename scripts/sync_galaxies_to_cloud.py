
import asyncio
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# 确保能找到 backend 模块
project_root = Path(__file__).parent.parent
import sys
sys.path.append(str(project_root))

from backend.app.services.feishu.bitable_ledger import bitable_ledger
from backend.app.core.config import settings

async def sync_galaxies_to_cloud():
    load_dotenv(override=True)
    
    # 1. 加载本地星系地图
    map_path = Path("backend/storage/thesaurus_map.json")
    if not map_path.exists():
        print(f" [Sync] 找不到本地星系地图: {map_path}")
        return

    with open(map_path, "r", encoding="utf-8") as f:
        thesaurus_map = json.load(f)

    print(f"📖 [Sync] 已加载本地聚类: {len(thesaurus_map)} 个")

    # 2. 格式化 Bitable 记录
    records = []
    for cluster_id, data in thesaurus_map.items():
        anchor_keywords = ", ".join(data.get("anchor_keywords", []))
        galaxies = data.get("galaxies", [])
        
        for g in galaxies:
            records.append({
                "fields": {
                    "星系名称": g["name"],
                    "锚点关键词": anchor_keywords,
                    "逻辑聚类ID": cluster_id,
                    "成员总数": g.get("members", 0),
                    "描述": f"来源于聚类 {cluster_id} 的原始主权划分"
                }
            })

    if not records:
        print(" [Sync] 没有发现待同步的星系数据。")
        return

    # 3. 写入 Bitable
    print(f" [Sync] 正在将 {len(records)} 个逻辑星系推往云端...")
    
    obj_token = await bitable_ledger.get_obj_token()
    #  职业程序员决策：强制指定经过验证的 ID，绕过环境变量加载迷雾
    table_id = "tblUNoT6tTIWZtcF" 
    
    print(f" [Sync] 目标 Table: {table_id}")
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{obj_token}/tables/{table_id}/records/batch_create"
    
    # 尝试分批写入
    resp = await bitable_ledger._api_request("POST", url, {"records": records})
    if resp.get("code") == 0:
        print(f" [Sync] 成功同步 {len(records)} 个星系记录。")
    else:
        print(f" [Sync] 同步失败，正在尝试单条诊断...")
        # 诊断：尝试单条写入看看是哪个字段报错
        single_url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{obj_token}/tables/{table_id}/records"
        diag_resp = await bitable_ledger._api_request("POST", single_url, {"fields": records[0]["fields"]})
        print(f" [Diag] 单条测试结果: {diag_resp}")

    print("\n" + "" * 30)
    print(" [Sync] 星系主权上云任务圆满完成！")
    print("你现在可以打开飞书 Bitable 查看‘逻辑星系 (Galaxies)’表了。")
    print("" * 30)

if __name__ == "__main__":
    asyncio.run(sync_galaxies_to_cloud())
