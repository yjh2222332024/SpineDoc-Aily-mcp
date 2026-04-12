
import numpy as np
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 sys.path，确保能导入 spine_cli
current_dir = Path(__file__).parent.parent
sys.path.append(str(current_dir))

from spine_cli.core.router import SemanticRouter

async def diagnostic():
    router = SemanticRouter()
    print(f"Testing router with model: {router.model}")

    # 测试 1: 短摘要编码能力
    summary = "DES 加密过程"
    query = "DES 是怎么加密的"
    
    summary_vec = await router.get_embedding(summary)
    query_vec = await router.get_embedding(query)
    
    score1 = router.cosine_similarity(summary_vec, query_vec)
    print(f"短摘要相似度：{score1:.3f}")

    # 测试 2: 长上下文编码能力
    summary_long = f"[STRUCTURE: 4 > 4.1] DES 加密过程包括初始置换、16 轮迭代、逆置换"
    summary_long_vec = await router.get_embedding(summary_long)
    
    score2 = router.cosine_similarity(summary_long_vec, query_vec)
    print(f"长上下文相似度：{score2:.3f}")

    if score1 < 0.45:
        print(f"RESULT: FAILURE - Score {score1:.3f} < 0.45 threshold (Current Settings)")
    else:
        print("RESULT: SUCCESS")

if __name__ == "__main__":
    asyncio.run(diagnostic())
