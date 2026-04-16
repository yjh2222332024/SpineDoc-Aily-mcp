"""
🌐 SpineDoc 联网证人 (V1.0 - Tavily SDK Edition)
职责：基于 Tavily SDK 执行外部检索，返回带权重的证据。
"""
import tavily
import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
from backend.app.core.config import settings
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    TavilyClient = None

from .color_confidence import ColorConfidenceCalculator, ConfidenceColor

logger = logging.getLogger(__name__)

# 🏛️ 配置常量（从 settings 读取）
TAVILY_API_KEY = settings.TAVILY_API_KEY
TAVILY_MAX_RESULTS = settings.TAVILY_MAX_RESULTS
TAVILY_SEARCH_DEPTH = settings.TAVILY_SEARCH_DEPTH
TAVILY_CONCURRENT_LIMIT = settings.TAVILY_CONCURRENT_LIMIT


class InternetWitness:
    """
    ⚖️ 联网证人：法庭的外部信息补充官。
    设计原则：故障隔离、异步友好、成本可控
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or TAVILY_API_KEY
        if TavilyClient and self.api_key:
            self.client = TavilyClient(api_key=self.api_key)
        else:
            self.client = None
        self._semaphore = asyncio.Semaphore(TAVILY_CONCURRENT_LIMIT)
        self.color_calc = ColorConfidenceCalculator()  # 四色置信度计算器

    async def summon(
        self,
        queries: List[str],
        query_type: str = 'RESEARCH'
    ) -> Dict:
        """
        🚀 传唤联网证人：并发执行查询

        Args:
            queries: 查询列表
            query_type: 查询类型（影响时间衰减）

        Returns:
            {
                "doc_id": "INTERNET_xxx",
                "galaxy_id": "INTERNET",
                "galaxy_name": "互联网证人",
                "evidence_chunks": [...],
                "is_internet": True
            }
        """
        if not self.client:
            logger.warning("⚠️ Tavily API Key 未配置，联网证人缺席。")
            return self._empty_package(error="Tavily API Key 未配置")

        print(f"📡 [InternetWitness] 正在执行 {len(queries)} 个子查询...")

        # 🏛️ 并发控制：信号量锁住单个请求，而非整个批处理
        # 这样多个用户可以同时传唤，但每个用户的查询会被节流
        tasks = [
            self._search_with_semaphore(query, query_type)
            for query in queries
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 合并结果
        all_chunks = []
        errors = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                err_msg = f"联网搜索异常 ({queries[i]}): {result}"
                logger.error(err_msg)
                errors.append(err_msg)
                continue
            all_chunks.extend(result)

        # 🚀 [V50.6] 如果所有查询都失败，返回错误包
        if not all_chunks:
            error_msg = "所有联网查询均失败：" + "; ".join(errors) if errors else "联网检索无结果"
            print(f"❌ [InternetWitness] {error_msg}")
            return self._empty_package(error=error_msg)

        print(f"✅ [InternetWitness] 检索到 {len(all_chunks)} 条外部证据")

        return {
            "doc_id": f"INTERNET_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "galaxy_id": "INTERNET",
            "galaxy_name": "互联网证人",
            "evidence_chunks": all_chunks,
            "scout_queries": queries,
            "is_internet": True
        }

    def _empty_package(self, error: str = "Tavily API 未配置或不可用") -> Dict:
        """返回空证据包"""
        return {
            "doc_id": "INTERNET_NA",
            "galaxy_id": "INTERNET",
            "galaxy_name": "互联网证人",
            "evidence_chunks": [],
            "scout_queries": [],
            "is_internet": True,
            "error": "Tavily API 未配置或不可用"
        }

    async def _search_with_semaphore(self, query: str, query_type: str) -> List[Dict]:
        """异步搜索单个查询，带信号量节流"""
        async with self._semaphore:
            return await asyncio.to_thread(self._search_single, query, query_type)

    def _search_single(self, query: str, query_type: str) -> List[Dict]:
        """同步搜索单个查询（在后台线程执行）"""
        if not self.client:
            return []

        try:
            response = self.client.search(
                query=query,
                search_depth=TAVILY_SEARCH_DEPTH,
                max_results=TAVILY_MAX_RESULTS,
                include_answer=True,
                include_raw_content=False
            )

            chunks = []
            for result in response.get('results', []):
                chunk_data = {
                    "id": f"internet_{result.get('url', '')[:20]}",
                    "content": result.get('content', ''),
                    "page_number": 0,  # 网页无页码
                    "breadcrumb": result.get('title', 'Internet Source'),
                    "logic_tags": [],
                    "source_url": result.get('url'),
                    "source_title": result.get('title'),
                    "published_date": result.get('published_date'),
                    "query_type": query_type,
                    "is_internet": True
                }
                # 计算颜色置信度
                color, confidence = self.color_calc.calculate(
                    chunk_data,
                    independent_sources=1,
                    has_conflict=False
                )
                chunk_data["color"] = color.value
                chunk_data["confidence"] = confidence
                chunks.append(chunk_data)

            return chunks
        except Exception as e:
            logger.error(f"Tavily 搜索失败 ({query}): {e}")
            return []
