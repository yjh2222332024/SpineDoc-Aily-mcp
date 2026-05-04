"""
OnlineRetriever - External information supplement via Zhipu Web Search API
============================================================================
Responsibility: Execute external web search, return weighted evidence chunks
with color-coded confidence scores. Replaces Tavily with Zhipu Web Search API.

替代旧名称：WitnessExpert
"""

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional

from zai import ZhipuAiClient

from backend.app.core.config import settings

from ..color_confidence import ColorConfidenceCalculator, ConfidenceColor

logger = logging.getLogger(__name__)

# Configuration constants (from settings)
ZHIPU_API_KEY = settings.ZHIPU_API_KEY
ZHIPU_SEARCH_ENGINE = settings.ZHIPU_SEARCH_ENGINE
ZHIPU_MAX_RESULTS = settings.ZHIPU_MAX_RESULTS
ZHIPU_CONTENT_SIZE = settings.ZHIPU_CONTENT_SIZE
ZHIPU_CONCURRENT_LIMIT = 5


class OnlineRetriever:
    """
    🚀 [V170.0] 证人专家：原子主张提取与稳定性确权。
    职责：
    1. 域外收割。
    2. 逻辑脱水：将网页长文解构为原子主张 (Atomic Claims)。
    3. 稳定性定级：判定知识时效，终结 1+1=2 悖论。
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ZHIPU_API_KEY
        if self.api_key:
            self.client = ZhipuAiClient(api_key=self.api_key)
        else:
            self.client = None
        self._semaphore = asyncio.Semaphore(ZHIPU_CONCURRENT_LIMIT)
        self.color_calc = ColorConfidenceCalculator()

    async def retrieve(self, queries: List[str], query_type: str = 'RESEARCH') -> Dict:
        """执行并发取证并执行逻辑脱水"""
        if not self.client:
            return self._empty_package(error="Zhipu API Key not configured")

        print(f"📡 [OnlineRetriever] 开始域外取证并在云端执行主张提取...")

        # 1. 物理取证
        tasks = [self._search_with_semaphore(query, query_type) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        raw_chunks = []
        for res in results:
            if not isinstance(res, Exception): raw_chunks.extend(res)

        if not raw_chunks:
            return self._empty_package(error="Online retrieval returned no results")

        # 2. 🚀 [V170.0] 逻辑质证：对 Top-5 证据进行云端解构
        # 为了效率，我们只对最相关的几个证据执行深度脱水
        top_chunks = raw_chunks[:2]
        print(f"🧠 [OnlineRetriever] 正在对 {len(top_chunks)} 条核心证据执行批量逻辑脱水...")
        from backend.app.services.ingestion.llm_service import llm_service

        refined_chunks = await self._batch_distill(top_chunks, llm_service)

        print(f"✅ [OnlineRetriever] 逻辑质证完成，提取出 {sum(len(c.get('claims', [])) for c in refined_chunks)} 条原子主张。")

        return {
            "doc_id": f"INTERNET_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "source_id": "INTERNET",
            "source_name": "Witness Expert",
            "evidence_chunks": refined_chunks,
            "is_online": True
        }

    async def _distill_evidence(self, chunk: Dict, llm) -> Dict:
        """
        调用云端算力，将片段解构为原子主张并定级稳定性。
        """
        prompt = f"""请作为联邦法院证人，对以下证据片段进行‘逻辑脱水’。
1. 提取出 3 条以内的【原子主张】（必须是确凿的事实陈述）。
2. 为该证据判定【稳定性等级】（0.0-1.0）：
   - 1.0: 永恒真理/公理（如 1+1=2, 数学公式, 物理定律）。
   - 0.8: 稳定知识（如 历史事实, 经典架构原则, 烹饪基本步骤）。
   - 0.3: 时效新闻/动态配置（如 天气, 实时股价, 软件版本更新）。

【证据内容】：
{chunk['content'][:1500]}

请严格输出 JSON 格式：{{"claims": ["主张1", "主张2"], "stability": 0.8}}
"""
        try:
            res = await llm.chat_completion(prompt, response_format="json")
            chunk["claims"] = res.get("claims", [])
            chunk["stability"] = float(res.get("stability", 0.5))

            # 🚀 覆盖置信度：稳定性高的证据，时间衰减影响减弱
            # 重新计算置信度颜色
            color, confidence = self.color_calc.calculate(
                chunk,
                independent_sources=1,
                has_conflict=False
            )

            # 🛡️ 架构师修正：如果稳定性极高，强行提分
            if chunk["stability"] >= 0.9:
                confidence = max(confidence, 0.95)
                color = "GREEN"

            chunk["color"] = str(color)
            chunk["confidence"] = confidence

        except Exception as e:
            chunk["claims"] = []
            chunk["stability"] = 0.5
            logger.warning(f"⚠️ [OnlineRetriever] 逻辑脱水失败: {e}")

        return chunk

    async def _batch_distill(self, chunks: List[Dict], llm) -> List[Dict]:
        """
        🚀 [Opt] 批量逻辑脱水：一次 LLM 调用处理多条证据，而非每条单独调。
        """
        # 构造批量 prompt：将所有证据内容编入一个 JSON 请求
        evidence_list = []
        for i, c in enumerate(chunks):
            evidence_list.append({
                "index": i,
                "content": c.get("content", "")[:1000]  # 每条截断 1000 字节省 token
            })

        prompt = f"""请作为联邦法院证人，对以下 {len(chunks)} 条证据片段进行批量‘逻辑脱水’。

对每条证据：
1. 提取出 3 条以内的【原子主张】（必须是确凿的事实陈述）。
2. 判定【稳定性等级】（0.0-1.0）：
   - 1.0: 永恒真理/公理
   - 0.8: 稳定知识
   - 0.3: 时效新闻/动态配置

【批量证据】：
{__import__('json').dumps(evidence_list, ensure_ascii=False, indent=2)}

请严格输出 JSON 数组格式：
[
  {{"index": 0, "claims": ["主张1", "主张2"], "stability": 0.8}},
  {{"index": 1, "claims": ["主张3"], "stability": 0.3}}
]
"""
        try:
            res = await llm.chat_completion(prompt, response_format="json")

            # 将结果按 index 映射回 chunks
            results_list = res if isinstance(res, list) else res.get("data", res.get("results", []))
            result_map = {}
            for item in results_list:
                idx = item.get("index")
                if idx is not None:
                    result_map[idx] = item

            for i, c in enumerate(chunks):
                item = result_map.get(i, {})
                c["claims"] = item.get("claims", [])
                c["stability"] = float(item.get("stability", 0.5))

                # 重新计算置信度颜色
                try:
                    color, confidence = self.color_calc.calculate(
                        c, independent_sources=1, has_conflict=False
                    )
                    if c["stability"] >= 0.9:
                        confidence = max(confidence, 0.95)
                        color = "GREEN"
                    c["color"] = str(color)
                    c["confidence"] = confidence
                except Exception:
                    c["color"] = "YELLOW"
                    c["confidence"] = 0.5

        except Exception as e:
            logger.warning(f"⚠️ [OnlineRetriever] 批量逻辑脱水失败: {e}")
            for c in chunks:
                c["claims"] = []
                c["stability"] = 0.5
                c["color"] = "YELLOW"
                c["confidence"] = 0.5

        return chunks

    def _empty_package(self, error: str = "Zhipu API not configured or unavailable") -> Dict:
        """Return empty evidence package"""
        return {
            "doc_id": "INTERNET_NA",
            "source_id": "INTERNET",
            "source_name": "Online Retriever",
            "evidence_chunks": [],
            "sub_queries": [],
            "is_online": True,
            "error": error
        }

    async def _search_with_semaphore(self, query: str, query_type: str) -> List[Dict]:
        """Async search single query with semaphore throttling"""
        async with self._semaphore:
            return await asyncio.to_thread(self._search_single, query, query_type)

    def _search_single(self, query: str, query_type: str) -> List[Dict]:
        """Sync search single query (executed in background thread)"""
        if not self.client:
            return []

        try:
            response = self.client.web_search.web_search(
                search_engine=ZHIPU_SEARCH_ENGINE,
                search_query=query,
                count=ZHIPU_MAX_RESULTS,
                content_size=ZHIPU_CONTENT_SIZE,
            )

            chunks = []
            for result in response.search_result or []:
                chunk_data = {
                    "id": f"zhipu_{hashlib.md5(result.link.encode()).hexdigest()[:8]}",
                    "content": result.content or "",
                    "page_number": 0,
                    "breadcrumb": result.title or "Web Source",
                    "logic_tags": [],
                    "source_url": result.link,
                    "source_title": result.title,
                    "published_date": result.publish_date,
                    "source_media": result.media,
                    "query_type": query_type,
                    "is_online": True,
                }
                color, confidence = self.color_calc.calculate(
                    chunk_data,
                    independent_sources=1,
                    has_conflict=False,
                )
                chunk_data["color"] = color.value
                chunk_data["confidence"] = confidence
                chunks.append(chunk_data)

            return chunks
        except Exception as e:
            logger.error(f"Zhipu web search failed ({query}): {e}")
            return []



WitnessExpert = OnlineRetriever

# 向后兼容别名
WitnessExpert = OnlineRetriever
