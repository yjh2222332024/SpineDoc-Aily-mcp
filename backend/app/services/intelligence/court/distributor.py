"""
⚖️ Distributor - 联邦法庭传唤官
=================================
职责：根据 query 和 ThesaurusMap 传唤相关文档证人。
"""

from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from backend.app.core.models import DocumentGalaxyLink, Galaxy
from backend.app.core.config import settings

from .thesaurus import ThesaurusManager
from .internet_witness import InternetWitness


class Distributor:
    """
    ⚖️ 传唤官 (The Summoner)

    职责：
    1. 读取 ThesaurusMap，找到 query 相关的 cluster
    2. 根据 cluster 找到相关的星系
    3. 通过 DocumentGalaxyLink 找到星系下的所有文档
    4. 返回传唤名单：[{'doc_id': '...', 'galaxy_id': '...', 'galaxy_name': '...'}]
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.thesaurus = ThesaurusManager()
        self.internet_witness = InternetWitness()  # 联网证人
        self.summoned_docs = []  # 保存传唤列表供测试访问

    async def summon_witnesses(self, query: str, limit_per_galaxy: int = None) -> List[Dict[str, str]]:
        """
        根据 query 传唤证人文档

        Args:
            query: 用户查询
            limit_per_galaxy: 每个星系最多传唤的文档数（默认从配置读取）

        Returns:
            summoned_docs: [{'doc_id': '...', 'galaxy_id': '...', 'galaxy_name': '...'}]
        """
        # 🚀 [V50.10] 从配置读取默认传唤限制
        if limit_per_galaxy is None:
            limit_per_galaxy = settings.COURT_SCOUT_QUERY_LIMIT
        # 1. 查询 Thesaurus，找到相关的 cluster
        cluster_ids = self.thesaurus.find_clusters_by_query(query)
        print(f"📋 [Distributor] 找到 {len(cluster_ids)} 个相关聚类：{cluster_ids}")

        # 2. 获取这些 cluster 下的所有星系 ID
        galaxy_ids = self.thesaurus.get_all_galaxy_ids(cluster_ids)
        print(f"📋 [Distributor] 覆盖 {len(galaxy_ids)} 个星系")

        if not galaxy_ids:
            # 兜底：按成员数量降序取前 settings.COURT_SCOUT_QUERY_LIMIT 个星系（防止全量召回导致 LLM 账单爆炸）
            print("⚠️ [Distributor] 无匹配聚类，使用成员最多的星系")
            stmt = select(Galaxy.id).order_by(Galaxy.member_count.desc()).limit(settings.COURT_SCOUT_QUERY_LIMIT)
            result = await self.session.execute(stmt)
            galaxy_ids = {str(g[0]) for g in result.all()}

        # 3. 查询 DocumentGalaxyLink，找到星系下的所有文档
        summoned_docs = []
        seen_doc_ids = set()

        for galaxy_id in galaxy_ids:
            stmt = select(DocumentGalaxyLink).where(
                DocumentGalaxyLink.galaxy_id == galaxy_id
            ).limit(limit_per_galaxy)

            result = await self.session.execute(stmt)
            links = result.scalars().all()

            for link in links:
                doc_id_str = str(link.document_id)
                galaxy_id_str = str(link.galaxy_id)

                # 去重：同一个文档可能被多个星系传唤
                if doc_id_str not in seen_doc_ids:
                    # 获取星系名称
                    galaxy_info = self.thesaurus.get_galaxy_info(galaxy_id_str)
                    galaxy_name = galaxy_info["name"] if galaxy_info else "Unknown"

                    summoned_docs.append({
                        "doc_id": doc_id_str,
                        "galaxy_id": galaxy_id_str,
                        "galaxy_name": galaxy_name
                    })
                    seen_doc_ids.add(doc_id_str)

        print(f"✅ [Distributor] 传唤完成：共 {len(summoned_docs)} 个证人文档")
        self.summoned_docs = summoned_docs  # 保存供测试访问
        return summoned_docs

    async def summon_internet_witness(self, scout_queries: List[str]) -> Dict:
        """
        传唤联网证人（返回单个证据包，包含所有查询的结果）

        Args:
            scout_queries: 子查询列表

        Returns:
            internet_package: {
                "doc_id": "INTERNET_xxx",
                "galaxy_id": "INTERNET",
                "galaxy_name": "互联网证人",
                "evidence_chunks": [...],
                "is_internet": True
            }
        """
        return await self.internet_witness.summon(scout_queries)

    async def summon_single_galaxy(self, galaxy_id: str, limit: int = 5) -> List[Dict[str, str]]:
        """
        从单个星系传唤证人（用于精确匹配场景）
        """
        stmt = select(DocumentGalaxyLink).where(
            DocumentGalaxyLink.galaxy_id == galaxy_id
        ).limit(limit)

        result = await self.session.execute(stmt)
        links = result.scalars().all()

        summoned_docs = []
        for link in links:
            galaxy_info = self.thesaurus.get_galaxy_info(str(link.galaxy_id))
            summoned_docs.append({
                "doc_id": str(link.document_id),
                "galaxy_id": str(link.galaxy_id),
                "galaxy_name": galaxy_info["name"] if galaxy_info else "Unknown"
            })

        return summoned_docs
