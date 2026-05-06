
"""
 SpineDoc Bitable Schema Architect
====================================
职责：在飞书多维表格中自动创建逻辑审计所需的标准字段。
"""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

# 字段契约定义 (基于飞书 API 类型)
# 1: 文本, 2: 数字, 3: 单选...
SCHEMA = [
    {"field_name": "审计问题", "type": 1},
    {"field_name": "判决结论", "type": 1},
    {"field_name": "置信度评分", "type": 2},
    {"field_name": "涉及星系", "type": 1},
    {"field_name": "风险状态", "type": 1},
    {"field_name": "矛盾描述", "type": 1},
    {"field_name": "逻辑进化摘要", "type": 1},
]

async def create_field(name, field_type, base_token, table_id, cli_path):
    # 飞书 API 字符串类型映射
    type_map = {1: "text", 2: "number", 3: "select"}
    
    field_config = {
        "name": name,
        "type": type_map.get(field_type, "text")
    }

    cmd = [
        cli_path, "base", "+field-create",
        "--base-token", base_token,
        "--table-id", table_id,
        "--json", json.dumps(field_config, ensure_ascii=False)
    ]
    print(f"🔨 正在创建字段: {name}...")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    if process.returncode == 0:
        print(f" 字段 '{name}' 创建成功")
    else:
        err_msg = stderr.decode()
        if "already exists" in err_msg or "Duplicate" in err_msg:
            print(f" 字段 '{name}' 已存在，跳过")
        else:
            print(f" 字段 '{name}' 创建失败: {err_msg}")

async def main():
    base_token = "XbXwbaFh7aNrNjsL80TcSozNnEh"
    table_id = "tblssBxwvGVTvSQJ"
    cli_path = "bin/lark-cli.exe"

    print(f" 开始为表 {table_id} 构建逻辑契约...")
    for field in SCHEMA:
        await create_field(field["field_name"], field["type"], base_token, table_id, cli_path)
    
    print("\n 地基构建完成！现在可以重新运行验证脚本了。")

if __name__ == "__main__":
    asyncio.run(main())
