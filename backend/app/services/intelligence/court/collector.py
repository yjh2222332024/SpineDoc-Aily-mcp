"""
📡 Collector - 联邦法庭取证器 (v2.0 证据分片版)
================================================
职责：并行执行单文档检索，直接返回证据分片供 Moderator 裁决。
不再调用 Integrator，因为多文档场景下只需要证据分片。
"""

import asyncio
import json
from typing import List, Dict
from uuid import UUID

from backend.app.services.rag.pyramid_harvester import PyramidHarvester
from backend.app.services.rag.vector_store import PostgresStore
from backend.app.core.db import get_async_sessionmaker
from backend.app.core.models import Chunk, TocItem
from sqlmodel import select
from openai import AsyncOpenAI
from backend.app.core.config import settings
from .internet_witness import InternetWitness
from .color_confidence import ColorConfidenceCalculator, ConfidenceColor


class Collector:
    """
    📡 取证器 (The Evidence Collector)

    职责：
    1. 接收传唤文档列表
    2. 为每个文档并行执行检索（Scout + Witness Collector + Examiner）
    3. 返回证据分片（不调用 Integrator）
    """

    def __init__(self):
        self.session_maker = get_async_sessionmaker()
        self.client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        self.internet_witness = InternetWitness()  # 联网证人
        self.color_calc = ColorConfidenceCalculator()  # 四色置信度计算器

    async def collect_evidence(
        self,
        summoned_docs: List[Dict[str, str]],
        query: str,
        enable_online: bool = False
    ) -> List[Dict]:
        """
        并行执行单文档检索，收集所有证据分片（包括联网证据）

        Args:
            summoned_docs: 传唤文档列表
            query: 原始查询
            enable_online: 是否激活联网证人

        Returns:
            evidence_packages: [{'doc_id': '...', 'galaxy_id': '...', 'galaxy_name': '...', 'evidence_chunks': [...], 'scout_queries': [...]}]
        """
        print(f"📡 [Collector] 开始取证，共 {len(summoned_docs)} 个证人...")
        if enable_online:
            print("🌐 [Collector] 联网证人已激活")

        # 1. Scout 拆解查询（用于联网检索）
        scout_queries = await self._scout(query)

        # 2. 并行：本地取证 + 联网取证（可选）
        local_tasks = [
            self._collect_local_doc(doc, query, scout_queries)
            for doc in summoned_docs
        ]

        # 联网取证（仅在 enable_online=True 时执行）
        internet_package = None
        if enable_online:
            print("🌐 [Collector] 正在传唤联网证人...")
            try:
                internet_result = await self.internet_witness.summon(scout_queries)

                # 检查联网结果是否有效
                if internet_result.get("error") or not internet_result.get("evidence_chunks"):
                    print(f"⚠️ [Collector] 联网证人返回空结果或错误")
                    raise Exception("联网检索无有效结果")

                internet_package = internet_result
                print("✅ [Collector] 联网证人取证成功")
            except Exception as e:
                # 🚀 [V50.6] 联网失败降级：sleep 3s + 明确日志 + 降级为无联网模式
                print(f"⚠️ [Collector] 联网证人取证失败：{e}")
                print(f"💤 [Collector] 联网服务不可用，休眠 {settings.TAVILY_FALLBACK_SLEEP_SECONDS}s 后降级为无联网模式...")
                await asyncio.sleep(settings.TAVILY_FALLBACK_SLEEP_SECONDS)
                print("🔌 [Collector] 已降级为无联网模式，继续本地取证...")

        # 只 gather 本地任务（都是 coroutines）
        results = await asyncio.gather(*local_tasks, return_exceptions=True)

        # 分离本地和联网结果
        evidence_packages = []
        for i, result in enumerate(results):
            # 本地证人
            doc_info = summoned_docs[i]
            if isinstance(result, Exception):
                print(f"⚠️ [Collector] 证人 {doc_info['doc_id'][:8]} 取证失败：{result}")
                evidence_packages.append({
                    "doc_id": doc_info["doc_id"],
                    "galaxy_id": doc_info["galaxy_id"],
                    "galaxy_name": doc_info["galaxy_name"],
                    "evidence_chunks": [],
                    "scout_queries": scout_queries,
                    "error": str(result)
                })
            else:
                evidence_packages.append(result)

        # 添加联网证据包（如果有）
        if internet_package:
            evidence_packages.append(internet_package)

        print(f"✅ [Collector] 取证完成：共 {len(evidence_packages)} 份证据包")
        return evidence_packages

    async def _collect_local_doc(
        self,
        doc: Dict[str, str],
        query: str,
        scout_queries: List[str]
    ) -> Dict:
        """
        单个本地文档的证据收集流程：
        1. PyramidHarvester: 针对 scout_queries 检索分片
        2. Examiner: 选择最相关的分片
        3. 返回证据分片
        """
        doc_id = doc["doc_id"]
        galaxy_id = doc["galaxy_id"]
        galaxy_name = doc["galaxy_name"]

        print(f"  📝 [Collector] 收集证据：{galaxy_name} → {doc_id[:8]}...")

        # --- Step 1: PyramidHarvester 检索 ---
        harvester = PyramidHarvester(PostgresStore())
        all_chunks = []
        seen_ids = set()

        for sub_query in scout_queries:
            chunks = await harvester.harvest(sub_query, doc_id=doc_id, limit=10)
            for chunk in chunks:
                if chunk['id'] not in seen_ids:
                    all_chunks.append(chunk)
                    seen_ids.add(chunk['id'])

        print(f"    ↳ 检索到 {len(all_chunks)} 个候选分片")

        # --- Step 2: Examiner 选择分片 ---
        selected_chunks = await self._examiner(query, all_chunks, doc_id)
        print(f"    ↳ Examiner 锁定 {len(selected_chunks)} 个核心分片")

        # --- Step 3: 读取完整分片内容 ---
        evidence_chunks = await self._load_chunks(selected_chunks)

        return {
            "doc_id": doc_id,
            "galaxy_id": galaxy_id,
            "galaxy_name": galaxy_name,
            "evidence_chunks": evidence_chunks,
            "scout_queries": scout_queries
        }

    async def _scout(self, query: str) -> List[str]:
        """Scout 节点：查询拆解"""
        prompt = f"""你是一个顶级的法医审计侦察员。你的任务是将一个复杂的审计问题拆解为 3 个具体的子任务。

【主问题】：{query}

要求：
1. 子任务必须是具体的、可检索的短句
2. 子任务之间应保持逻辑互补
3. 严格输出 JSON 对象格式：{{"sub_queries": ["q1", "q2", "q3"]}}
"""
        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2
            )
            data = json.loads(response.choices[0].message.content)
            return data.get("sub_queries", [query])
        except:
            return [query]

    async def _examiner(
        self,
        query: str,
        chunks: List[Dict],
        doc_id: str
    ) -> List[Dict]:
        """Examiner 节点：选择最相关的分片"""
        # 加载 TOC
        toc = await self._load_toc(doc_id)

        # 构造指纹库
        fingerprint_pool = [
            {"id": c["id"], "p": c["page_number"], "path": c["breadcrumb"], "tags": c.get("logic_tags", [])[:settings.CONTEXT_LOGIC_TAGS_LIMIT]}
            for c in chunks
        ]

        # 🚀 [V50.10] 从配置读取 TOC 截取上限
        toc_limit = settings.COURT_CONTEXT_TOC_LIMIT

        prompt = f"""你是一个严谨的法医审计质证员。选出最能回答问题的证据分片。

【目标文档逻辑脊梁 (TOC)】:
{json.dumps(toc[:toc_limit], ensure_ascii=False)}

【待选证据指纹库】:
{json.dumps(fingerprint_pool, ensure_ascii=False)}

【原始审计问题】:
{query}

你的任务：
1. 交叉比对问题、TOC 路径与指纹关键词
2. 剔除"语义漂移"项
3. 选出 3-5 个最具代表性的 Chunk ID
4. 严格输出 JSON 数组格式：{{"selected_ids": ["uuid1", "uuid2"]}}
"""
        try:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            data = json.loads(response.choices[0].message.content)
            selected_ids = set(data.get("selected_ids", [])[:settings.CONTEXT_SELECTED_IDS_LIMIT])

            # 兜底：如果 LLM 没选，取 RRF 分数最高的
            if not selected_ids and chunks:
                sorted_chunks = sorted(chunks, key=lambda x: x.get('rrf_score', 0), reverse=True)
                return sorted_chunks[:settings.CONTEXT_FALLBACK_CHUNKS]

            # 返回选中的分片
            return [c for c in chunks if c["id"] in selected_ids]
        except Exception as e:
            print(f"  ⚠️ Examiner 异常：{e}，使用兜底策略")
            sorted_chunks = sorted(chunks, key=lambda x: x.get('rrf_score', 0), reverse=True)
            return sorted_chunks[:settings.CONTEXT_FALLBACK_CHUNKS]

    async def _load_toc(self, doc_id: str) -> List[Dict]:
        """加载文档 TOC"""
        async with self.session_maker() as session:
            stmt = select(TocItem).where(TocItem.document_id == doc_id).order_by(TocItem.page)
            result = await session.execute(stmt)
            toc_items = result.scalars().all()
            return [{"title": t.title, "page": t.page, "level": t.level, "physical_start": t.physical_start} for t in toc_items]

    async def _load_chunks(self, selected_chunks: List[Dict]) -> List[Dict]:
        """从数据库加载完整分片内容，并计算颜色置信度"""
        chunk_ids = [c["id"] for c in selected_chunks if c.get("id")]
        if not chunk_ids:
            return []

        async with self.session_maker() as session:
            stmt = select(Chunk).where(Chunk.id.in_([UUID(cid) for cid in chunk_ids]))
            result = await session.execute(stmt)
            chunks = result.scalars().all()

            evidence_chunks = []
            for c in chunks:
                chunk_data = {
                    "id": str(c.id),
                    "content": c.content,
                    "page_number": c.page_number,
                    "breadcrumb": c.breadcrumb,
                    "logic_tags": c.logic_tags,
                    "type": "LOCAL_PDF",
                    "doc_status": getattr(c, 'doc_status', 'completed'),
                }
                # 计算本地证据颜色置信度
                color, confidence = self.color_calc.calculate(
                    chunk_data,
                    independent_sources=1,
                    has_conflict=False
                )
                chunk_data["color"] = color.value
                chunk_data["confidence"] = confidence
                evidence_chunks.append(chunk_data)

            return evidence_chunks
