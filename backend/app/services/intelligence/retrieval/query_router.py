"""
QueryRouter - Routes queries to relevant document sources
=========================================================
Responsibility: Find relevant documents from Bitable for a given query.
"""

from typing import List, Dict
from backend.app.core.config import settings

from .term_map_manager import TermMapManager
from .online_retriever import OnlineRetriever


class QueryRouter:
    """
    QueryRouter - Routes queries to relevant document sources

    Responsibilities:
    1. List all processed documents from Bitable
    2. Match query against document metadata (name, tags)
    3. Return routing list: [{'doc_id': '...', 'source_id': '...', 'source_name': '...'}]
    """

    def __init__(self):
        self.term_map = TermMapManager()
        self.online_retriever = OnlineRetriever()
        self.retrieved_sources = []

    async def route_query(self, query: str, limit_per_source: int = None) -> List[Dict[str, str]]:
        """
        Route query to relevant document sources.
        Fetches all processed documents from Bitable and filters by query relevance.
        """
        from backend.app.services.feishu.bitable_ledger import bitable_ledger

        app_token = await bitable_ledger._get_app_token()
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{bitable_ledger.tables['docs']}/records/search"

        payload = {
            "filter": {
                "conjunction": "and",
                "conditions": [
                    {"field_name": "处理状态", "operator": "is", "value": ["PROCESSED"]}
                ]
            },
            "page_size": 50
        }

        resp = await bitable_ledger._api_request("POST", url, json_data=payload)
        items = resp.get("data", {}).get("items", [])

        sources = []
        query_lower = query.lower()

        for it in items:
            f = it.get("fields", {})
            filename = f.get("文件名", "")
            doc_id = it.get("record_id", "")

            if not doc_id:
                continue

            # Simple relevance: match query against filename
            # For richer matching, this could use TermMap or LLM-based relevance
            relevance = query_lower in filename.lower() or any(
                word in filename.lower() for word in query_lower.split() if len(word) > 2
            )

            sources.append({
                "doc_id": doc_id,
                "source_id": doc_id,
                "source_name": filename or f"Document {doc_id[:8]}",
                "relevance": relevance
            })

        # Sort: relevant docs first, then by recency (most recent first)
        sources.sort(key=lambda s: (s["relevance"]), reverse=True)

        # Filter to only relevant docs if we have any, otherwise return all
        if any(s["relevance"] for s in sources):
            sources = [s for s in sources if s["relevance"]]

        if sources:
            print(f"[QueryRouter] Routed {len(sources)} documents for query")
        else:
            print("[QueryRouter] No relevant documents found")

        return sources

    async def route_online(self, sub_queries: List[str]) -> Dict:
        """
        Route to online retriever
        """
        return await self.online_retriever.retrieve(sub_queries)

    async def route_single_source(self, source_id: str, limit: int = 5) -> List[Dict[str, str]]:
        """
        Route to a single source (deprecated)
        """
        return []