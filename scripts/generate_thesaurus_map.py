"""
🧬 Thesaurus Map v2.0 - 工业级聚类重组员
=========================================
使命：基于人工打标测算的 0.72 阈值，执行跨文档语义聚合。
纪律：拒绝魔法数字，拥抱物理测算，实现“主权归类”。
"""

import asyncio
import json
import numpy as np
import os
import sys
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# 🏛️ 路径锚定
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.app.core.config import settings
from backend.app.core.models import Galaxy, Chunk, DocumentGalaxyLink
from backend.app.services.keyword_extractor import get_keyword_extractor

def cosine_similarity(v1: np.ndarray, v2: np.ndarray) -> float:
    """计算两个向量的余弦相似度"""
    dot = np.dot(v1, v2)
    norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)
    if norm_product == 0:
        return 0.0
    return float(dot / norm_product)

async def generate_industrial_thesaurus(threshold: float = 0.72):
    print("\n" + "🔭 " * 20)
    print(f"🚀 [Thesaurus v2.0] 启动工业级重组 (阈值: {threshold})")
    print("🔭 " * 20)

    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    keyword_extractor = get_keyword_extractor()
    # 建立噪音防御网
    stopwords = keyword_extractor.stopwords | keyword_extractor.ACADEMIC_BOILERPLATE | keyword_extractor.WEAK_WORDS

    async with async_session() as session:
        # 1. 加载所有活跃星系
        print("\n📊 [1] 加载星系数据...")
        stmt = select(Galaxy).where(Galaxy.member_count > 0)
        res = await session.execute(stmt)
        galaxies = res.scalars().all()
        
        if not galaxies:
            print("⚠️ 没有活跃星系")
            return

        galaxy_vectors = {
            str(g.id): {
                "name": g.name, 
                "vec": np.array(g.centroid_embedding),
                "members": g.member_count
            } for g in galaxies
        }
        g_ids = list(galaxy_vectors.keys())
        print(f"   发现 {len(g_ids)} 个活跃星系")

        # 2. 并查集聚类 (Union-Find)
        print("\n🧩 [2] 构建逻辑集群 (并查集)...")
        parent = {gid: gid for gid in g_ids}
        
        def find(i):
            if parent[i] == i: return i
            parent[i] = find(parent[i])
            return parent[i]
            
        def union(i, j):
            root_i, root_j = find(i), find(j)
            if root_i != root_j:
                parent[root_i] = root_j

        for i in range(len(g_ids)):
            for j in range(i + 1, len(g_ids)):
                v1, v2 = galaxy_vectors[g_ids[i]]["vec"], galaxy_vectors[g_ids[j]]["vec"]
                sim = cosine_similarity(v1, v2)
                if sim >= threshold:
                    union(g_ids[i], g_ids[j])
                    print(f"   🔗 关联: {galaxy_vectors[g_ids[i]]['name']} ↔ {galaxy_vectors[g_ids[j]]['name']} ({sim:.4f})")

        # 3. 收集聚类并执行“深度指纹提取”
        print("\n🧬 [3] 执行跨文档指纹聚合与主权命名...")
        clusters = {}
        for gid in g_ids:
            root = find(gid)
            if root not in clusters: 
                clusters[root] = []
            clusters[root].append(gid)

        industrial_map = {}
        for idx, (root, members) in enumerate(clusters.items(), 1):
            cluster_id = f"cluster_{idx}"
            member_names = [galaxy_vectors[m]["name"] for m in members]
            
            # 聚合关键词 (统计词频)
            word_cloud = {}
            for gid in members:
                # 🚀 跨表查询：从该星系关联的所有 Chunk 中捞取关键词
                chunk_stmt = select(Chunk.logic_tags).join(
                    DocumentGalaxyLink, DocumentGalaxyLink.document_id == Chunk.document_id
                ).where(DocumentGalaxyLink.galaxy_id == gid)
                chunk_res = await session.execute(chunk_stmt)
                
                for tags in chunk_res.scalars().all():
                    if not tags: continue
                    for t in tags:
                        t_clean = t.lower().strip()
                        # 物理去噪
                        if t_clean not in stopwords and len(t_clean) > 1 and not t_clean.isdigit():
                            word_cloud[t] = word_cloud.get(t, 0) + 1
            
            # 选取 Top 8 最具代表性的词作为集群锚点 (增加到 8 个，提高语义覆盖)
            top_anchors = sorted(word_cloud.items(), key=lambda x: -x[1])[:8]
            anchor_keywords = [w[0] for w in top_anchors]
            
            # 兜底命名逻辑
            if not anchor_keywords:
                anchor_keywords = list(set([n.replace("Galaxy_", "").split("_")[0] for n in member_names]))

            industrial_map[cluster_id] = {
                "anchor_keywords": anchor_keywords,
                "galaxies": [
                    {
                        "id": m, 
                        "name": galaxy_vectors[m]["name"], 
                        "members": galaxy_vectors[m]["members"]
                    } for m in members
                ]
            }
            print(f"   ✅ {cluster_id}: {anchor_keywords}")

        # 4. 保存到物理存储
        output_path = os.path.join(settings.STORAGE_ROOT, "thesaurus_map.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(industrial_map, f, ensure_ascii=False, indent=2)

    print(f"\n💾 [4] 工业级地图已保存至: {output_path}")
    print(f"   共生成 {len(industrial_map)} 个逻辑集群。")
    print("\n✨ 完成。")

if __name__ == "__main__":
    # 允许通过命令行指定阈值
    import sys
    target_threshold = 0.72
    if len(sys.argv) > 1:
        try:
            target_threshold = float(sys.argv[1])
        except: pass
        
    asyncio.run(generate_industrial_thesaurus(target_threshold))
