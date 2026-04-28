import asyncio
import json
import subprocess
from typing import Dict, Any

CLI_PATH = "bin/lark-cli.exe"

async def run_cli(args: list) -> Dict[str, Any]:
    cmd = [CLI_PATH] + args
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode == 0:
        try:
            return json.loads(stdout.decode())
        except json.JSONDecodeError:
            return {"raw": stdout.decode()}
    else:
        raise RuntimeError(f"CLI Error: {stderr.decode()}")

async def setup_ledger():
    print("🚀 [Genesis] 开始构建 SpineDoc 云端逻辑总账...")

    # 1. 创建 Base
    print("🏗️ [Step 1] 创建多维表格 (Base)...")
    base_res = await run_cli(["base", "+base-create", "--name", "🦴 [SpineDoc] 云端逻辑总账", "--folder-token", ""])
    app_token = base_res.get("data", {}).get("base", {}).get("base_token")
    if not app_token:
        print("❌ 创建 Base 失败", base_res)
        return
    print(f"✅ Base 创建成功! App Token: {app_token}")

    # 2. 创建 Documents 数据表
    print("🏗️ [Step 2] 配置 Documents 数据表...")
    doc_table_res = await run_cli(["base", "+table-create", "--base-token", app_token, "--name", "Documents"])
    doc_table_id = doc_table_res.get("data", {}).get("table", {}).get("id")
    if not doc_table_id:
        print("❌ 创建 Documents 表失败", doc_table_res)
        return
    print(f"✅ Documents 表创建成功! Table ID: {doc_table_id}")
    
    # 增加 Documents 字段
    fields_doc = [
        {"field_name": "文件名", "type": "text"},
        {"field_name": "文件哈希", "type": "text"},
        {"field_name": "总页数", "type": "number"},
        {"field_name": "处理状态", "type": "text"},
    ]
    for f in fields_doc:
        print(f"   ↳ 添加字段: {f['field_name']}")
        field_json = json.dumps({"field_name": f["field_name"], "type": f["type"]}, ensure_ascii=False)
        await run_cli(["base", "+field-create", "--base-token", app_token, "--table-id", doc_table_id, "--json", field_json])

    # 3. 创建 Chunks 表
    print("🏗️ [Step 3] 创建 Chunks 数据表...")
    chunk_table_res = await run_cli(["base", "+table-create", "--base-token", app_token, "--name", "Chunks"])
    chunk_table_id = chunk_table_res.get("data", {}).get("table", {}).get("id")
    print(f"✅ Chunks 表创建成功! Table ID: {chunk_table_id}")

    # 增加 Chunks 字段
    fields_chunk = [
        {"field_name": "文档关联", "type": "text"},
        {"field_name": "正文内容", "type": "text"},
        {"field_name": "物理页码", "type": "number"},
        {"field_name": "逻辑面包屑", "type": "text"},
        {"field_name": "Git版本", "type": "text"},
    ]
    for f in fields_chunk:
        print(f"   ↳ 添加字段: {f['field_name']}")
        field_json = json.dumps({"field_name": f["field_name"], "type": f["type"]}, ensure_ascii=False)
        await run_cli(["base", "+field-create", "--base-token", app_token, "--table-id", chunk_table_id, "--json", field_json])

    # 4. 🚀 [V59.0] 创建 TOC_Items 表 (逻辑脊梁摘要)
    print("🏗️ [Step 4] 配置 TOC_Items 数据表...")
    toc_table_res = await run_cli(["base", "+table-create", "--base-token", app_token, "--name", "TOC_Items"])
    toc_table_id = toc_table_res.get("data", {}).get("table", {}).get("id")
    print(f"✅ TOC 表创建成功! Table ID: {toc_table_id}")

    fields_toc = [
        {"field_name": "标题", "type": "text"},
        {"field_name": "层级", "type": "number"},
        {"field_name": "逻辑页码", "type": "number"},
        {"field_name": "豆包逻辑摘要", "type": "text"}, # 这里存储 AI 判词
        {"field_name": "文档关联", "type": "text"},
    ]
    for f in fields_toc:
        print(f"   ↳ 添加字段: {f['field_name']}")
        field_json = json.dumps({"field_name": f["field_name"], "type": f["type"]}, ensure_ascii=False)
        await run_cli(["base", "+field-create", "--base-token", app_token, "--table-id", toc_table_id, "--json", field_json])

    print("\n" + "="*50)
    print("🎉 [Genesis] 创世完成！请更新 .env：")
    print(f"FEISHU_BITABLE_TOKEN={app_token}")
    print(f"FEISHU_BITABLE_TABLE_ID={doc_table_id}")
    print(f"FEISHU_BITABLE_CHUNK_TABLE_ID={chunk_table_id}")
    print(f"FEISHU_BITABLE_TOC_TABLE_ID={toc_table_id}")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(setup_ledger())
