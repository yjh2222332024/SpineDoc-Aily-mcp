import asyncio
from sqlalchemy import text
from app.core.db import get_async_engine

async def migrate():
    engine = get_async_engine()
    async with engine.begin() as conn:
        print("🚀 [Migration] 正在注入 Nexus 核心架构...")
        
        # 1. 注入 Document 全局画像字段
        await conn.execute(text("ALTER TABLE document ADD COLUMN IF NOT EXISTS nexus_atlas JSONB DEFAULT '{}';"))
        
        # 2. 注入 Chunk 逻辑基因字段
        await conn.execute(text("ALTER TABLE chunk ADD COLUMN IF NOT EXISTS logic_tags JSONB DEFAULT '[]';"))
        await conn.execute(text("ALTER TABLE chunk ADD COLUMN IF NOT EXISTS causality_links JSONB DEFAULT '{}';"))
        await conn.execute(text("ALTER TABLE chunk ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT 1.0;"))
        
        # 3. 建立三元组 GIN 索引（V35.0 高性能过滤）
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_chunk_logic_tags ON chunk USING GIN (logic_tags jsonb_path_ops);"))
        
        print("✅ [Migration] Nexus 基石已奠定。")

if __name__ == "__main__":
    asyncio.run(migrate())
