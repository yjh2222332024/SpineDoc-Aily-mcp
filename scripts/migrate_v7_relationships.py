"""
数据库迁移脚本 - V7.0 逻辑织网协议

功能:
  1. 创建 chunk_relationships 表
  2. 添加 relationship_type 枚举类型
  3. 创建索引优化查询性能
  4. 添加外键约束保证引用完整性

用法:
    python scripts/migrate_v7_relationships.py

作者：SpineDoc Team
日期：2026-04-16
"""

import sys
import os

# 添加项目根目录到路径 (兼容 Windows)
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 添加 backend 目录 (因为 app 在 backend 下)
backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

from sqlalchemy import create_engine, text, inspect

# 使用同步引擎进行迁移（asyncpg 不支持同步上下文）
# 从配置模块导入，保证和应用使用同一个数据库
from backend.app.core.config import settings
DATABASE_URL = settings.DATABASE_URL
# 转换为同步 psycopg2 驱动
SYNC_DATABASE_URL = DATABASE_URL.replace("asyncpg", "psycopg2")

def check_table_exists(engine, table_name: str) -> bool:
    """检查表是否已存在"""
    with engine.connect() as conn:
        inspector = inspect(engine)
        return table_name in inspector.get_table_names()

def migrate():
    """执行 V7.0 迁移"""
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║    SpineDoc V7.0 - 逻辑织网协议数据库迁移                ║")
    print("╚═══════════════════════════════════════════════════════════╝")

    engine = create_engine(SYNC_DATABASE_URL)

    # 检查是否已迁移
    if check_table_exists(engine, "chunk_relationships"):
        print("\n   chunk_relationships 表已存在，跳过迁移")
        print("    如需重新迁移，请先删除表：DROP TABLE chunk_relationships CASCADE;")
        return

    print("\n📋 开始执行迁移...")

    with engine.connect() as conn:
        # 1. 创建 relationship_type 枚举类型（如果不存在）
        print("   [1/5] 创建 RelationshipType 枚举类型...")
        conn.execute(text("""
            DO $$ BEGIN
                CREATE TYPE relationship_type AS ENUM (
                    'causality',        -- A 导致 B，或 A 是 B 的前提
                    'contradiction',    -- A 与 B 存在逻辑冲突
                    'support',          -- A 为 B 提供证据支撑
                    'evolution',        -- B 是 A 的修正版本
                    'complement'        -- A 和 B 描述同一实体的不同维度
                );
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """))
        print("   ✓ 枚举类型创建完成")

        # 2. 创建 chunk_relationships 表
        print("   [2/5] 创建 chunk_relationships 表...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chunk_relationships (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

                -- 关系两端
                source_chunk_id UUID NOT NULL REFERENCES chunk(id) ON DELETE CASCADE,
                target_chunk_id UUID NOT NULL REFERENCES chunk(id) ON DELETE CASCADE,

                -- 关系谓词（使用枚举类型）
                rel_type relationship_type NOT NULL,

                -- 关系强度
                strength FLOAT NOT NULL DEFAULT 1.0 CHECK (strength >= 0.0 AND strength <= 1.0),

                -- 关系描述
                description TEXT,

                -- 证据溯源
                verdict_id UUID,

                -- 元数据
                created_by VARCHAR(255) NOT NULL DEFAULT 'GraphWeaver',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

                -- 防止重复关系（同一对 Chunk 不能有相同类型的关系）
                UNIQUE(source_chunk_id, target_chunk_id, rel_type)
            );
        """))
        print("   ✓ chunk_relationships 表创建完成")

        # 3. 创建索引
        print("   [3/5] 创建索引优化查询性能...")

        # source_chunk 索引（用于查询出边）
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_relationships_source
            ON chunk_relationships(source_chunk_id);
        """))

        # target_chunk 索引（用于查询入边）
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_relationships_target
            ON chunk_relationships(target_chunk_id);
        """))

        # rel_type 索引（用于按关系类型筛选）
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_relationships_type
            ON chunk_relationships(rel_type);
        """))

        # verdict_id 索引（用于追溯审判记录）
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_relationships_verdict
            ON chunk_relationships(verdict_id);
        """))

        # 复合索引（用于双向查询）
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_relationships_both
            ON chunk_relationships(source_chunk_id, target_chunk_id);
        """))

        print("   ✓ 索引创建完成 (5 个索引)")

        # 4. 添加注释（表说明）
        print("   [4/5] 添加表注释...")
        conn.execute(text("""
            COMMENT ON TABLE chunk_relationships IS
            ' [V7.0] 逻辑织网协议 - Chunk 关系表，承载审判后的质证结论';

            COMMENT ON COLUMN chunk_relationships.rel_type IS
            '关系谓词：causality(因果), contradiction(矛盾), support(证据), evolution(演进), complement(补充)';

            COMMENT ON COLUMN chunk_relationships.strength IS
            '关系强度 0.0-1.0，由 Moderator 裁决时评估';

            COMMENT ON COLUMN chunk_relationships.verdict_id IS
            '触发此关系的 Court Verdict ID，用于证据溯源';
        """))
        print("   ✓ 表注释添加完成")

        # 5. 提交事务
        print("   [5/5] 提交事务...")
        conn.commit()
        print("   ✓ 事务提交成功")

    print("\n" + "═" * 65)
    print(" V7.0 迁移完成！")
    print("\n📊 新增内容:")
    print("   - chunk_relationships 表")
    print("   - relationship_type 枚举类型")
    print("   - 5 个查询索引")
    print("\n🔗 下一步:")
    print("   1. 运行 'spine check' 验证配置")
    print("   2. 实现 GraphWeaver 服务")
    print("   3. 升级 Moderator Prompt 支持关系识别")
    print("═" * 65)


if __name__ == "__main__":
    try:
        migrate()
    except Exception as e:
        print(f"\n 迁移失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
