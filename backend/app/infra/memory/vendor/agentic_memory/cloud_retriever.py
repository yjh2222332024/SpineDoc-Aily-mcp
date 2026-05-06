"""
CloudRetriever — ChromaDB-free semantic neighbor finder
=======================================================
Uses Bitable for persistent storage and GLM Cloud embeddings
for vectorization. Cosine similarity computed in-memory with numpy.
"""
import json
import logging
from typing import Dict, List, Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


class CloudRetriever:
    """
    Cloud-native retriever replacing ChromaDB.
    Storage: Bitable records (chunks table with memory marker).
    Embedding: SiliconFlow BGE-M3 via embedding_service.
    Similarity: numpy cosine similarity (in-memory, O(n) for <1000 items).
    """

    def __init__(self, table_id: str):
        self.table_id = table_id

    async def add_document(self, document: str, metadata: Dict, doc_id: str):
        from backend.app.services.feishu.bitable_ledger import bitable_ledger
        from backend.app.services.ingestion.embedding import embedding_service

        vector = await embedding_service.get_embeddings(document)
        if not vector:
            logger.warning(f"[CloudRetriever] Empty embedding for doc {doc_id}")
            return

        processed_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, (list, dict)):
                processed_metadata[key] = json.dumps(value)
            else:
                processed_metadata[key] = str(value)

        fields = {
            "记忆ID": doc_id,
            "正文内容": document,
            "元数据": json.dumps(processed_metadata),
            "向量表征": json.dumps(vector[0]),
        }

        payload = {"fields": fields}
        url = (
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/"
            f"{bitable_ledger.app_token}/tables/{self.table_id}/records"
        )
        resp = await bitable_ledger._api_request("POST", url, payload)
        record_id = resp.get("data", {}).get("record", {}).get("record_id")
        if record_id:
            logger.info(f"[CloudRetriever] Added doc {doc_id} -> record {record_id[:8]}")

    async def delete_document(self, doc_id: str):
        from backend.app.services.feishu.bitable_ledger import bitable_ledger

        search_url = (
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/"
            f"{bitable_ledger.app_token}/tables/{self.table_id}/records/search"
        )
        resp = await bitable_ledger._api_request(
            "POST", search_url,
            json_data={"filter": {"conjunction": "and", "conditions": [
                {"field_name": "记忆ID", "operator": "is", "value": [doc_id]}
            ]}}
        )
        items = resp.get("data", {}).get("items", [])
        if not items:
            logger.warning(f"[CloudRetriever] Doc {doc_id} not found for deletion")
            return

        record_id = items[0].get("record_id")
        delete_url = (
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/"
            f"{bitable_ledger.app_token}/tables/{self.table_id}/records/{record_id}"
        )
        await bitable_ledger._api_request("DELETE", delete_url)
        logger.info(f"[CloudRetriever] Deleted doc {doc_id}")

    async def search(self, query: str, k: int = 5) -> Dict[str, Any]:
        """
        Find k nearest memories by cosine similarity.
        Returns same format as ChromaDB:
        {'ids': [[...]], 'documents': [[...]], 'metadatas': [[...]], 'distances': [[...]]}
        """
        from backend.app.services.feishu.bitable_ledger import bitable_ledger
        from backend.app.services.ingestion.embedding import embedding_service

        query_vector = np.array(await embedding_service.get_embeddings(query))[0]

        search_url = (
            f"https://open.feishu.cn/open-apis/bitable/v1/apps/"
            f"{bitable_ledger.app_token}/tables/{self.table_id}/records/search"
        )
        resp = await bitable_ledger._api_request(
            "POST", search_url, json_data={
                "page_size": 500,
            }
        )
        items = resp.get("data", {}).get("items", [])

        if not items:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        ids = []
        docs = []
        metas = []
        distances = []

        for item in items:
            f = item.get("fields", {})
            vec_str = f.get("向量表征", "[]")
            try:
                vec = np.array(
                    json.loads(vec_str) if isinstance(vec_str, str) else vec_str
                )
            except Exception:
                continue

            norm_q = np.linalg.norm(query_vector)
            norm_v = np.linalg.norm(vec)
            if norm_q == 0 or norm_v == 0:
                continue

            similarity = float(np.dot(query_vector, vec) / (norm_q * norm_v))
            meta_json = f.get("元数据", "{}")
            try:
                meta = (
                    json.loads(meta_json)
                    if isinstance(meta_json, str)
                    else meta_json
                )
            except Exception:
                meta = {}

            memory_id = f.get("记忆ID", item.get("record_id", ""))
            content = f.get("正文内容", "")

            ids.append(memory_id)
            docs.append(content)
            metas.append(meta)
            distances.append(similarity)

        if not ids:
            return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

        top_indices = np.argsort(distances)[::-1][:k]
        return {
            "ids": [[ids[i] for i in top_indices]],
            "documents": [[docs[i] for i in top_indices]],
            "metadatas": [[metas[i] for i in top_indices]],
            "distances": [[float(distances[i]) for i in top_indices]],
        }
