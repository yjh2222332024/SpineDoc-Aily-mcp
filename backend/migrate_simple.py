"""
极简同步迁移脚本
"""
import sys
import os
from sqlalchemy import create_engine, text

# 尝试获取同步版本的 DATABASE_URL
# 如果是 postgresql+asyncpg://... 改为 postgresql://...
db_url = os.environ.get("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/spinedoc")
if "+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "")

print(f"🔗 正在连接数据库: {db_url}")

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        print("📝 尝试添加 metadata_json 列...")
        conn.execute(text("ALTER TABLE chunk ADD COLUMN IF NOT EXISTS metadata_json JSONB DEFAULT '{}'::jsonb"))
        conn.commit()
        print("✅ 执行成功 (或列已存在)")
except Exception as e:
    print(f"❌ 失败: {e}")
