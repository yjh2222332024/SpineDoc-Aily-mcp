"""
ClusterEngine — Recursive Abstractive Knowledge Engine (V3.1)
===========================================================
Responsibility:
1. Projects chunks into semantic clusters (Galaxies).
2. Performs recursive summarization (RAPTOR Level 1+).
3. Maintains physical 'Parent Link' consistency in Bitable.
"""

import numpy as np
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)

class ClusterEngine:
    """
    Cloud-native knowledge clustering and recursive summarization engine.
    """
    def __init__(self, store=None):
        from backend.app.services.feishu.bitable_ledger import bitable_ledger
        manifest_path = Path("backend/storage/bitable_schema_manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            self.manifest = json.load(f)
        self.store = store or bitable_ledger
        self.similarity_threshold = 0.85
        self.distill_threshold = 5 

    async def assign_chunk(self, chunk_rec_id: str, chunk_data: Dict[str, Any]):
        """
        将分片分配到星系，并自动触发演化与可能的递归。
        """
        # 🛡️ 强制防御：审计入库分片结构
        if not isinstance(chunk_data, dict):
            logger.error(f"❌ [Cluster] 入库数据非字典: {type(chunk_data)}")
            return

        vector = chunk_data.get("embedding")
        if not vector or len(vector) != 2048:
            logger.warning(f"⚠️ [Cluster] Chunk {chunk_rec_id[:8]} 向量无效，分配失败。")
            return


        clusters = await self._fetch_all_clusters()
        best_cluster_id, max_score = self._find_best_match(vector, clusters)

        if not clusters:
            best_cluster_id = await self._create_cluster(chunk_data, vector)
            max_score = 1.0

        if max_score > self.similarity_threshold:
            print(f"🧲 [Cluster] Strong match ({max_score:.2f}) -> {best_cluster_id[:8]}")
            await self._link_to_cluster(chunk_rec_id, best_cluster_id, vector)
            await self._check_and_distill(best_cluster_id)
        else:
            if best_cluster_id:
                print(f"🔗 [Cluster] Weak match ({max_score:.2f}), mounting to existing cluster: {best_cluster_id[:8]}")
                await self._link_to_cluster(chunk_rec_id, best_cluster_id, vector)
            else:
                new_id = await self._create_cluster(chunk_data, vector)
                if new_id: await self._link_to_cluster(chunk_rec_id, new_id, vector)

    def _find_best_match(self, vector: List[float], clusters: List[Dict]) -> Tuple[Optional[str], float]:
        best_id, max_s = None, -1.0
        v1 = np.array(vector)
        for c in clusters:
            v2 = c.get("centroid_embedding")
            if not v2: continue
            v2_arr = np.array(v2)
            if len(v1) != len(v2_arr): continue
            score = float(np.dot(v1, v2_arr) / (np.linalg.norm(v1) * np.linalg.norm(v2_arr)))
            if score > max_s:
                max_s = score
                best_id = c["record_id"]
        return best_id, max_s

    async def _check_and_distill(self, cluster_id: str):
        await self.distill_cluster(cluster_id)

    async def distill_cluster(self, cluster_rec_id: str):
        children = await self.store.fetch_chunks_by_galaxy(cluster_rec_id)
        if len(children) < self.distill_threshold:
            return 

        print(f"🔭 [RAPTOR] Cluster {cluster_rec_id[:8]} reached density. Distilling Level 1...")
        summary, tags = await self._call_llm_distillation(children)

        # 健壮取值：修复 NoneType 错误
        doc_rec_id = next((c.get("doc_record_id") for c in children if c.get("doc_record_id")), None)
        if not doc_rec_id:
            logger.error(f"❌ [Distill] 星系 {cluster_rec_id[:8]} 子分片缺失文档关联ID")
            return

        parent_chunk = {
            "content": f"🌌 星系共识：{summary}",
            "logic_summary": summary,
            "logic_tags": tags,
            "level": 1,
            "parent_id": [c["id"] for c in children],
            "breadcrumb": f"GalaxySummary/{cluster_rec_id[:8]}",
            "page_number": -1 
        }

        await self.store.save_chunks_batch(doc_rec_id, [parent_chunk])
        print(f"✅ [RAPTOR] Level 1 node established.")

    async def _call_llm_distillation(self, children: List[Dict]) -> Tuple[str, List[str]]:
        from backend.app.services.rag.llm import llm_service
        context = "\n---\n".join([f"摘要: {c.get('summary', '')}\n内容: {c.get('content', '')[:50]}" for c in children[:10]])
        prompt = f"提炼知识共识摘要（100字内）与3个标签：\n{context}"
        resp = await llm_service.chat_completion(prompt, response_format="json")
        return resp.get("summary", "逻辑共识"), resp.get("tags", ["Consensus"])

    async def _create_cluster(self, chunk_data: Dict, vector: List[float]) -> str:
        raw_tags = chunk_data.get("logic_tags") or ["Misc"]
        normalized_tags = [t.get("text") if isinstance(t, dict) else str(t) for t in raw_tags]
        
        name = f"Galaxy_{normalized_tags[0].title().replace(' ', '_')}"
        table_info = self.manifest["tables"]["galaxies"]
        
        payload = {"fields": {
            table_info["fields"]["name"]: name,
            table_info["fields"]["anchor_keywords"]: normalized_tags,
            table_info["fields"]["member_count"]: 0,
            table_info["fields"]["centroid_embedding"]: json.dumps(vector),
            table_info["fields"]["description"]: "自动演化领地"
        }}
        resp = await self.store._api_request("POST", f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.manifest['base_token']}/tables/{table_info['id']}/records", payload)
        return resp.get("data", {}).get("record", {}).get("record_id")

    async def _fetch_all_clusters(self) -> List[Dict]:
        table_info = self.manifest["tables"]["galaxies"]
        resp = await self.store._api_request("GET", f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.manifest['base_token']}/tables/{table_info['id']}/records")
        items = resp.get("data", {}).get("items", [])
        return [{"record_id": it["record_id"], "centroid_embedding": json.loads(it["fields"].get(table_info["fields"]["centroid_embedding"], "[]"))} for it in items]

    async def _link_to_cluster(self, chunk_id: str, cluster_id: str, vector: List[float]):
        chunk_table_id = self.manifest["tables"]["chunks"]["id"]
        
        payload = {"fields": {
            "星系关联": [cluster_id], 
            "向量表征": json.dumps(vector)
        }}
        
        app_token = self.manifest["base_token"]
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{chunk_table_id}/records/{chunk_id}"
        
        await self.store._api_request("PUT", url, payload)
        await self._evolve_centroid(cluster_id, vector)

    async def _evolve_centroid(self, cluster_id: str, new_vector: List[float]):
        table_info = self.manifest["tables"]["galaxies"]
        resp = await self.store._api_request("GET", f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.manifest['base_token']}/tables/{table_info['id']}/records/{cluster_id}")
        fields = resp.get("data", {}).get("record", {}).get("fields", {})
        count = fields.get(table_info["fields"]["member_count"], 0)
        new_count = count + 1
        
        vec_str = fields.get(table_info["fields"]["centroid_embedding"], "[]")
        old_vec = np.array(json.loads(vec_str)) if isinstance(vec_str, str) and vec_str != "[]" else None
        
        update_fields = {table_info["fields"]["member_count"]: new_count}
        if old_vec is not None and len(old_vec) == len(new_vector):
            updated_vec = (old_vec * count + np.array(new_vector)) / new_count
            update_fields[table_info["fields"]["centroid_embedding"]] = json.dumps(updated_vec.tolist())
        else:
            update_fields[table_info["fields"]["centroid_embedding"]] = json.dumps(new_vector)

        await self.store._api_request("PUT", f"https://open.feishu.cn/open-apis/bitable/v1/apps/{self.manifest['base_token']}/tables/{table_info['id']}/records/{cluster_id}", {"fields": update_fields})
        print(f"🧬 [Evolution] Galaxy {cluster_id[:8]} updated ({new_count})")

cluster_engine = ClusterEngine()
