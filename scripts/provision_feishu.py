#!/usr/bin/env python3
"""
SpineDoc Feishu 一键配置
=======================
自动检测/创建多维表格、数据表、字段。
幂等：已有表/字段不会重复创建，不会删除任何数据。

用法:
  python scripts/provision_feishu.py                # 交互模式
  python scripts/provision_feishu.py --yes          # 自动模式(供 bat 调用)
"""
import asyncio
import os
import sys
from pathlib import Path

import httpx

API_BASE = "https://open.feishu.cn/open-apis"

# ─── 表结构定义 ───────────────────────────────────────
# type: 1=文本 2=数字 4=多选 7=关联

TABLES = [
    {
        "key": "documents", "name": "文档表",
        "fields": [
            {"field_name": "文件名", "type": 1},
            {"field_name": "文件哈希", "type": 1},
            {"field_name": "处理状态", "type": 1},
            {"field_name": "总页数", "type": 2},
        ],
        "links": [],
    },
    {
        "key": "galaxies", "name": "星系表",
        "fields": [
            {"field_name": "星系名称", "type": 1},
            {"field_name": "重心向量", "type": 1},
            {"field_name": "锚点关键词", "type": 4},
            {"field_name": "成员总数", "type": 2},
            {"field_name": "描述", "type": 1},
            {"field_name": "锚点标签云", "type": 1},
        ],
        "links": [],
    },
    {
        "key": "toc", "name": "脊梁表",
        "fields": [
            {"field_name": "标题", "type": 1},
            {"field_name": "层级", "type": 2},
            {"field_name": "逻辑页码", "type": 2},
            {"field_name": "逻辑坐标", "type": 1},
        ],
        "links": [
            {"field_name": "文档关联", "type": 7, "target_key": "documents", "multiple": False},
        ],
    },
    {
        "key": "chunks", "name": "Chunk表",
        "fields": [
            {"field_name": "正文内容", "type": 1},
            {"field_name": "逻辑摘要", "type": 1},
            {"field_name": "语义标签", "type": 4},
            {"field_name": "逻辑坐标", "type": 1},
            {"field_name": "逻辑面包屑", "type": 1},
            {"field_name": "逻辑指纹", "type": 1},
            {"field_name": "向量表征", "type": 1},
            {"field_name": "Git版本", "type": 1},
            {"field_name": "物理页码", "type": 2},
            {"field_name": "元数据", "type": 1},
            {"field_name": "记忆ID", "type": 1},
        ],
        "links": [
            {"field_name": "文档关联", "type": 7, "target_key": "documents", "multiple": False},
            {"field_name": "星系关联", "type": 7, "target_key": "galaxies", "multiple": True},
            {"field_name": "父级关联", "type": 7, "target_key": "chunks", "multiple": True},
        ],
    },
    {
        "key": "memory", "name": "记忆表",
        "fields": [
            {"field_name": "记忆ID", "type": 1},
            {"field_name": "正文内容", "type": 1},
            {"field_name": "元数据", "type": 1},
            {"field_name": "向量表征", "type": 1},
        ],
        "links": [],
    },
]


# ─── API 客户端 ──────────────────────────────────────

class FeishuClient:
    def __init__(self, token: str):
        self.token = token
        self._headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def _req(self, method: str, url: str, **kw) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.request(method, url, headers=self._headers, **kw)
            d = r.json()
            if d.get("code") != 0:
                raise RuntimeError(f"API 错误: {d.get('msg', d)}")
            return d

    async def get(self, url: str) -> dict:
        return await self._req("GET", url)

    async def post(self, url: str, payload: dict = None) -> dict:
        return await self._req("POST", url, json=payload or {})

    async def create_bitable(self, name: str = "SpineDoc") -> str:
        d = await self.post(f"{API_BASE}/bitable/v1/apps", {"name": name})
        return d["data"]["app"]["app_token"]

    async def list_tables(self, app_token: str) -> list:
        d = await self.get(f"{API_BASE}/bitable/v1/apps/{app_token}/tables?page_size=50")
        return d.get("data", {}).get("items", [])

    async def create_table(self, app_token: str, name: str) -> str:
        d = await self.post(f"{API_BASE}/bitable/v1/apps/{app_token}/tables", {"name": name})
        return d["data"]["table_id"]

    async def list_fields(self, app_token: str, table_id: str) -> list:
        d = await self.get(f"{API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/fields?page_size=100")
        return d.get("data", {}).get("items", [])

    async def create_field(self, app_token: str, table_id: str, field: dict):
        await self.post(f"{API_BASE}/bitable/v1/apps/{app_token}/tables/{table_id}/fields", field)


# ─── 工具 ────────────────────────────────────────────

def confirm(prompt: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    ans = input(f"{prompt} ({hint}): ").strip().lower()
    if not ans:
        return default
    return ans[0] == "y"


def update_env_file(env_path: Path, updates: dict, force: bool = False):
    if env_path.exists() and not force:
        if not confirm(".env 已存在，更新其中的飞书配置?", True):
            print("  - 跳过 .env")
            return

    lines = env_path.read_text(encoding="utf-8").splitlines(True) if env_path.exists() else []
    existing_keys = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("#") and not stripped.startswith(";"):
            key = stripped.split("=", 1)[0].strip()
            existing_keys.add(key)
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                continue
        new_lines.append(line)

    for k, v in updates.items():
        if k not in existing_keys:
            new_lines.append(f"{k}={v}\n")

    env_path.write_text("".join(new_lines), encoding="utf-8")
    print(f"  ✓ .env 已更新: {env_path}")


async def main_async(force: bool = False):
    print("═" * 52)
    print("  SpineDoc 飞书多维表格配置")
    print("  幂等操作：已有表/字段不会重复创建")
    print("═" * 52)

    # ── 1. 认证 ──
    if force:
        # 非交互模式：从环境变量或 args 读取
        app_id = os.environ.get("FEISHU_APP_ID", "")
        app_secret = os.environ.get("FEISHU_APP_SECRET", "")
        if not app_id or not app_secret:
            print("✗ --yes 模式需要设置 FEISHU_APP_ID / FEISHU_APP_SECRET 环境变量")
            sys.exit(1)
    else:
        app_id = input("\nApp ID: ").strip()
        app_secret = input("App Secret: ").strip()

    if not app_id or not app_secret:
        print("✗ App ID 和 App Secret 不能为空")
        sys.exit(1)

    print("\n[1/5] 认证...")
    async with httpx.AsyncClient(timeout=20.0) as c:
        r = await c.post(f"{API_BASE}/auth/v3/tenant_access_token/internal",
                         json={"app_id": app_id, "app_secret": app_secret})
        d = r.json()
        if "tenant_access_token" not in d:
            print(f"✗ 认证失败: {d.get('msg', d)}")
            sys.exit(1)
        token = d["tenant_access_token"]
    print("  ✓ 认证成功")

    fc = FeishuClient(token)

    # ── 2. 选择/创建多维表格 ──
    print("\n[2/5] 多维表格...")
    app_token = os.environ.get("FEISHU_BITABLE_TOKEN", "")
    if app_token:
        print(f"  ✓ 使用现有 base: {app_token}")
    elif force:
        app_token = await fc.create_bitable()
        print(f"  ✓ 新建 base: {app_token}")
    else:
        inp = input("使用已有多维表格? (输入 app_token, 留空新建): ").strip()
        app_token = inp if inp else await fc.create_bitable()
        print(f"  ✓ {'使用已有' if inp else '新建'} base: {app_token}")

    # ── 3. 检测/创建数据表 ──
    print("\n[3/5] 检测数据表...")
    existing_table_map = {t["name"]: t["table_id"] for t in await fc.list_tables(app_token)}

    table_ids = {}
    for tdef in TABLES:
        if tdef["name"] in existing_table_map:
            tid = existing_table_map[tdef["name"]]
            print(f"  ✓ {tdef['name']}: {tid} (已存在)")
        else:
            tid = await fc.create_table(app_token, tdef["name"])
            print(f"  + {tdef['name']}: {tid} (新建)")
        table_ids[tdef["key"]] = tid

    # ── 4. 检测/创建字段 ──
    print("\n[4/5] 检测字段 (已有的跳过)...")

    for tdef in TABLES:
        tid = table_ids[tdef["key"]]
        existing_fields = {f["field_name"]: f for f in await fc.list_fields(app_token, tid)}

        for fdef in tdef["fields"]:
            if fdef["field_name"] in existing_fields:
                continue
            try:
                await fc.create_field(app_token, tid, fdef)
                print(f"  + {tdef['name']}.{fdef['field_name']}")
            except RuntimeError as e:
                if "duplicate" in str(e).lower():
                    continue
                print(f"  ⚠ {tdef['name']}.{fdef['field_name']}: {e}")

        for ldef in tdef["links"]:
            fn = ldef["field_name"]
            if fn in existing_fields:
                continue
            link_field = {
                "field_name": fn, "type": 7,
                "property": {"table_id": table_ids[ldef["target_key"]], "multiple": ldef["multiple"]},
            }
            try:
                await fc.create_field(app_token, tid, link_field)
                print(f"  + {tdef['name']}.{fn} → {ldef['target_key']}")
            except RuntimeError as e:
                if "duplicate" in str(e).lower():
                    continue
                print(f"  ⚠ {tdef['name']}.{fn}: {e}")

    # ── 5. 写入配置 ──
    print("\n[5/5] 写入环境变量...")

    update_env_file(project_root / ".env", {
        "FEISHU_BITABLE_TOKEN": app_token,
        "FEISHU_BITABLE_TABLE_ID": table_ids["documents"],
        "FEISHU_BITABLE_CHUNK_TABLE_ID": table_ids["chunks"],
        "FEISHU_BITABLE_TOC_TABLE_ID": table_ids["toc"],
        "FEISHU_BITABLE_MEMORY_TABLE_ID": table_ids["memory"],
        "FEISHU_BITABLE_GALAXY_TABLE_ID": table_ids["galaxies"],
    }, force=force)

    print("\n" + "═" * 52)
    print("  配置完成！")
    print(f"  Base Token: {app_token}")
    print("═" * 52)


def main():
    force = "--yes" in sys.argv or "-y" in sys.argv
    if force:
        sys.argv = [a for a in sys.argv if a not in ("--yes", "-y")]
    asyncio.run(main_async(force=force))


if __name__ == "__main__":
    main()
