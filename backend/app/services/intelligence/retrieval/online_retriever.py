"""
OnlineRetriever - External information supplement via Zhipu Web Search API
============================================================================
Responsibility: Execute external web search, return weighted evidence chunks
with color-coded confidence scores. Replaces Tavily with Zhipu Web Search API.
"""

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Dict, List, Optional

from zai import ZhipuAiClient

from backend.app.core.config import settings

from .color_confidence import ColorConfidenceCalculator, ConfidenceColor

logger = logging.getLogger(__name__)

# Configuration constants (from settings)
ZHIPU_API_KEY = settings.ZHIPU_API_KEY
ZHIPU_SEARCH_ENGINE = settings.ZHIPU_SEARCH_ENGINE
ZHIPU_MAX_RESULTS = settings.ZHIPU_MAX_RESULTS
ZHIPU_CONTENT_SIZE = settings.ZHIPU_CONTENT_SIZE
ZHIPU_CONCURRENT_LIMIT = 5


class OnlineRetriever:
    """
    OnlineRetriever: External information supplement for the retrieval system.
    Powered by Zhipu Web Search API — structured results with native publish_date.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ZHIPU_API_KEY
        if self.api_key:
            self.client = ZhipuAiClient(api_key=self.api_key)
        else:
            self.client = None
        self._semaphore = asyncio.Semaphore(ZHIPU_CONCURRENT_LIMIT)
        self.color_calc = ColorConfidenceCalculator()

    async def retrieve(
        self,
        queries: List[str],
        query_type: str = 'RESEARCH'
    ) -> Dict:
        """
        Execute queries concurrently

        Args:
            queries: Query list
            query_type: Query type (affects time decay)

        Returns:
            {
                "doc_id": "INTERNET_xxx",
                "source_id": "INTERNET",
                "source_name": "Online Retriever",
                "evidence_chunks": [...],
                "is_online": True
            }
        """
        if not self.client:
            logger.warning("⚠️ Zhipu API Key not configured, online retriever unavailable.")
            return self._empty_package(error="Zhipu API Key not configured")

        print(f"📡 [OnlineRetriever] Executing {len(queries)} sub-queries via Zhipu Web Search...")

        tasks = [
            self._search_with_semaphore(query, query_type)
            for query in queries
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_chunks = []
        errors = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                err_msg = f"Online search exception ({queries[i]}): {result}"
                logger.error(err_msg)
                errors.append(err_msg)
                continue
            all_chunks.extend(result)

        if not all_chunks:
            error_msg = "All online queries failed: " + "; ".join(errors) if errors else "Online retrieval returned no results"
            print(f"❌ [OnlineRetriever] {error_msg}")
            return self._empty_package(error=error_msg)

        print(f"✅ [OnlineRetriever] Retrieved {len(all_chunks)} external evidence pieces")

        return {
            "doc_id": f"INTERNET_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "source_id": "INTERNET",
            "source_name": "Online Retriever",
            "evidence_chunks": all_chunks,
            "sub_queries": queries,
            "is_online": True
        }

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
