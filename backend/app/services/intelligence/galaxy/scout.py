import numpy as np
from uuid import UUID, uuid4
from typing import List, Dict, Any, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.models import Chunk, Galaxy, DocumentGalaxyLink, Document, TocItem
from backend.app.services.rag.vector_store import PostgresStore
from backend.app.services.keyword_extractor import get_keyword_extractor
from backend.app.services.intelligence.galaxy.utils.anchor_auditor import AdvancedAnchorAuditor
from backend.app.core.config import settings

class GalaxyScout:
    """
    🔭 逻辑星系侦察员 (V3.0 - Industrial Governance Edition)
    职责：结合向量引力与高级语义审计，执行“入库即归档”的净化聚类。
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.vector_store = PostgresStore()
        self.keyword_extractor = get_keyword_extractor()
        self.auditor = AdvancedAnchorAuditor(use_cross_encoder=True)

    async def get_document_profile(self, doc_id: UUID) -> Dict[str, Any]:
        """
        🚀 测量文档"主权指纹"：加权向量 + 核心关键词集 + 原始文本上下文。
        """
        stmt = select(TocItem.embedding, TocItem.level, TocItem.title).where(TocItem.document_id == doc_id)
        result = await self.session.execute(stmt)
        rows = result.all()

        if not rows: return {"vector": None, "keywords": [], "context": ""}

        # 1. 语义高通滤波：屏蔽学术噪音
        generic_noise = {"introduction", "related work", "methodology", "experiment", "experimental", "setup",
                         "conclusion", "conclution", "results", "appendix", "bibliography", "references", "limitations"}

        weighted_vectors = []
        titles_for_keywords = []
        total_weight = 0.0

        for vec, level, title in rows:
            if vec is None: continue
            clean_title = title.lower().strip()

            # 仅在非噪音章节提取指纹，并增加权重
            if clean_title not in generic_noise:
                titles_for_keywords.append(title)
                weight = float(level) ** 2
            else:
                weight = 0.1 # 噪音权重

            weighted_vectors.append(np.array(vec) * weight)
            total_weight += weight

        context_text = " ".join(titles_for_keywords)

        # 2. 提取指纹 (保持重要性排序)
        fingerprints = self.keyword_extractor.extract_keywords(context_text, top_n=15)

        # 🚀 [V51.3] 过滤 "synthetic" 污染词（TOC 扫描失败时的兜底标记）
        fingerprints = [kw for kw in fingerprints if kw.lower() != "synthetic" and "synthetic" not in kw.lower()]

        # 🚀 [V2.0] 赫布学习：将提取出的关键词反馈给全局词库，实现自演进
        self.keyword_extractor.vocab.record_document(set(fingerprints))

        essence_vector = np.sum(np.array(weighted_vectors), axis=0) / total_weight if total_weight > 0 else None

        return {
            "id": doc_id,
            "vector": essence_vector,
            "keywords": fingerprints,
            "context": context_text[:2000] # 提供给审计员的上下文
        }

    async def discover_galaxy_clusters(self, similarity_threshold: float = 0.88) -> List[Dict[str, Any]]:
        """
        🔭 发现星系：向量为主，关键词指纹执行"一票否决"。
        """
        stmt = select(Document.id, Document.filename).where(Document.status == "completed")
        result = await self.session.execute(stmt)
        docs_info = result.all()

        profiles = []
        for d_id, name in docs_info:
            p = await self.get_document_profile(d_id)
            if p["vector"] is not None:
                p["name"] = name
                profiles.append(p)

        if not profiles: return []

        # 增强聚类
        clusters = []
        visited = set()
        n = len(profiles)

        for i in range(n):
            if i in visited: continue

            new_cluster = [profiles[i]["id"]]
            visited.add(i)
            p1 = profiles[i]

            print(f"\n🔍 [Audit] 以 '{p1['name']}' 为中心寻找星系...")

            # 这里的关键词对比需要转回 set
            p1_ks = set(p1["keywords"])

            for j in range(n):
                if i == j or j in visited: continue
                p2 = profiles[j]
                p2_ks = set(p2["keywords"])

                # A. 向量相似度
                vec_sim = np.dot(p1["vector"], p2["vector"]) / (np.linalg.norm(p1["vector"]) * np.linalg.norm(p2["vector"]))

                # B. 关键词 Jaccard
                intersection = p1_ks.intersection(p2_ks)
                union = p1_ks.union(p2_ks)
                kw_sim = len(intersection) / len(union) if union else 0.0

                if vec_sim > similarity_threshold:
                    if kw_sim > 0 or vec_sim > 0.95:
                        new_cluster.append(p2["id"])
                        visited.add(j)

            clusters.append({
                "suggested_name": f"Galaxy_{p1['name'][:10]}",
                "document_ids": new_cluster,
                "centroid": p1["vector"].tolist(),
                "keywords": list(p1_ks)
            })

        return clusters

    async def project_document_to_galaxies(self, doc_id: UUID):
        """
        🚀 工业级投影 (V5.0 - Industrial Governance)
        职责：通过“审计安检 + 密度预检”，实现入库即归档，拒绝垃圾星系。
        """
        profile = await self.get_document_profile(doc_id)
        if not profile["keywords"] or profile["vector"] is None:
            return []

        # --- Step 1: 语义审计 (The Auditor) ---
        # 过滤掉非领域词汇，保留高纯度锚点
        audited_anchors = self.auditor.audit_keywords(
            profile["keywords"], 
            profile["context"],
            top_n=3
        )
        
        if not audited_anchors:
            print(f"⚠️ [Galaxy] 文档 {doc_id} 未能提取到高质量锚点，进入 [Misc] 星系")
            audited_anchors = ["Misc"]

        projected_galaxies = []
        for anchor in audited_anchors:
            anchor_name = f"Galaxy_{anchor.title().replace(' ', '_')}"
            
            # --- Step 2: 密度预检 (Similarity Probing) ---
            # 寻找是否存在极度相似的已有星系 (> 0.92)
            similar_galaxy = await self._find_similar_galaxy(profile["vector"])
            
            if similar_galaxy:
                print(f"🧲 [Galaxy] 捕获到强引力：文档归并至相似星系 '{similar_galaxy.name}' (similarity > 0.92)")
                await self._link_document_to_galaxy(doc_id, similar_galaxy, 1.0, profile)
                projected_galaxies.append(similar_galaxy.name)
            else:
                # 正常创建或获取硬匹配星系
                galaxy = await self._get_or_create_anchor_galaxy(anchor_name, anchor, profile)
                await self._link_document_to_galaxy(doc_id, galaxy, 1.0, profile)
                projected_galaxies.append(galaxy.name)

        await self.session.commit()
        return list(set(projected_galaxies))

    async def _find_similar_galaxy(self, document_vector: np.ndarray, threshold: float = 0.92) -> Optional[Galaxy]:
        """
        密度预检：探测向量空间中是否存在强邻居。
        """
        # 1. 加载所有活跃星系
        stmt = select(Galaxy).where(Galaxy.member_count > 0)
        res = await self.session.execute(stmt)
        all_galaxies = res.scalars().all()
        
        best_match = None
        max_sim = -1.0
        
        v1 = document_vector
        norm_v1 = np.linalg.norm(v1)
        
        for g in all_galaxies:
            v2 = np.array(g.centroid_embedding)
            norm_v2 = np.linalg.norm(v2)
            if norm_v1 == 0 or norm_v2 == 0: continue
            
            sim = np.dot(v1, v2) / (norm_v1 * norm_v2)
            if sim > max_sim:
                max_sim = sim
                best_match = g
                
        if max_sim >= threshold:
            return best_match
            
        return None

    async def _get_or_create_anchor_galaxy(self, name: str, anchor_word: str, profile: Dict[str, Any]) -> Galaxy:
        """
        寻找已有的锚点星系，或物理创建一个新的。
        """
        stmt = select(Galaxy).where(Galaxy.name == name)
        res = await self.session.execute(stmt)
        existing = res.scalars().first()

        if existing:
            return existing

        # 创立新星系
        print(f"🌑 [Galaxy] 发现新语义锚点 '{anchor_word}'，正在初始化星系...")
        new_galaxy = Galaxy(
            id=uuid4(),
            name=name,
            description=f"以语义锚点 '{anchor_word}' 为核心的主权领域",
            centroid_embedding=profile["vector"].tolist(),
            member_count=0
        )
        self.session.add(new_galaxy)
        await self.session.flush()
        return new_galaxy

    async def _link_document_to_galaxy(self, doc_id: UUID, galaxy: Galaxy, score: float, profile: Dict[str, Any]):
        """
        🧬 建立关联并执行"人口加权"重心演化 (Population-Weighted Evolution)
        """
        # 1. 检查是否已存在关联 (幂等性保护)
        existing_stmt = select(DocumentGalaxyLink).where(
            DocumentGalaxyLink.document_id == doc_id,
            DocumentGalaxyLink.galaxy_id == galaxy.id
        )
        existing_res = await self.session.execute(existing_stmt)
        if existing_res.scalars().first():
            return

        # 2. 建立物理关联
        link = DocumentGalaxyLink(
            document_id=doc_id,
            galaxy_id=galaxy.id,
            relevance_score=float(score),
            perspective_summary=f"Projected via Anchor: {galaxy.name.split('_')[-1]}"
        )
        self.session.add(link)

        # 3. 🚀 人口加权演化：确保语义主权不丢失
        count = galaxy.member_count
        old_centroid = np.array(galaxy.centroid_embedding)
        new_vector = np.array(profile["vector"])

        updated_centroid = (old_centroid * count + new_vector) / (count + 1)

        # 更新状态
        galaxy.centroid_embedding = updated_centroid.tolist()
        galaxy.member_count = count + 1 # 物理计数递增

        print(f"✨ [Galaxy] 关联完成：{galaxy.name} (成员数：{galaxy.member_count})")


    async def establish_galaxy(self, name: str, description: str, doc_ids: List[UUID]):
        """
        人工确权逻辑 (Admin Override)
        """
        # TODO: 实现由用户手动指定的星系建立逻辑
        pass
