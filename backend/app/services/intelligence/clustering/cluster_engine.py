"""
ClusterEngine — Recursive Abstractive Knowledge Engine (V3.3)
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

class ClusterEngine:
    """
    Cloud-native knowledge clustering and recursive summarization engine.
    """
    def __init__(self, store=None):
        from backend.app.services.feishu.bitable_ledger import bitable_ledger
        self.logger = logging.getLogger(__name__)
        self.store = store or bitable_ledger
        self.similarity_threshold = 0.65
        self.distill_threshold = 5 

    async def assign_chunk(self, chunk_rec_id: str, chunk_data: Dict[str, Any]):
        """将分片分配到星系：执行强引力归属或弱引力创世"""
        vector = chunk_data.get("embedding")
        if not vector or len(vector) != 2048:
            return

        clusters = await self._fetch_all_clusters()
        best_cluster_id, max_score = self._find_best_match(vector, clusters)

        #  逻辑确权：平衡阈值设定为 0.65
        # 如果相似度太低，强制创世（Genesis），防止语义黑洞
        if best_cluster_id and max_score > self.similarity_threshold:
            print(f"🧲 [Cluster] Strong match ({max_score:.2f}) -> Joining Galaxy {best_cluster_id[:8]}")
            await self._link_to_cluster(chunk_rec_id, best_cluster_id, vector)
            chunk_data["galaxy_id"] = best_cluster_id  # 供入库冲突检测用
            # 检查是否需要蒸馏（RAPTOR 核心）
            await self._check_and_distill(best_cluster_id)
        else:
            reason = "No clusters exist" if not best_cluster_id else f"Weak match ({max_score:.2f} < {self.similarity_threshold})"
            print(f"🌌 [Genesis] {reason} -> Creating new Galaxy...")
            new_id = await self._create_cluster(chunk_data, vector)
            if new_id:
                await self._link_to_cluster(chunk_rec_id, new_id, vector)
                chunk_data["galaxy_id"] = new_id  # 供入库冲突检测用

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
        """
        RAPTOR 核心：汇总内容并由 Bitable AI 完成摘要。
        """
        children = await self.store.fetch_chunks_by_galaxy(cluster_rec_id)
        if len(children) < self.distill_threshold: return 

        print(f"🔭 [RAPTOR] Cluster {cluster_rec_id[:8]} reached density. Aggregating for Cloud AI...")
        
        # 汇总子节点内容，作为 Bitable AI 摘要字段的输入源
        #  架构师守则：不再浪费 Token 调 LLM，相信 Bitable 的物理蒸馏
        context = "\n---\n".join([f"分片内容: {c.get('content', '')}" for c in children[:15]])
        
        doc_rec_id = next((c.get("doc_record_id") for c in children if c.get("doc_record_id")), None)
        if not doc_rec_id: return

        # 2. 物理化 Level 1 共识节点
        parent_chunk = {
            "content": f"🌌 [星系共识基座 - {cluster_rec_id[:8]}]\n{context}",
            "page_number": -1,
            "logic_coord": f"L1-{cluster_rec_id[:8]}",
            "breadcrumb": f"GalaxySummary/{cluster_rec_id[:8]}",
            "parent_id": [c["id"] for c in children]
        }
        
        #  物理确权：保存父节点。Bitable 会根据“正文内容”自动生成“逻辑摘要”
        parent_ids = await self.store.save_chunks_batch(doc_rec_id, [parent_chunk])
        if parent_ids:
            new_parent_id = parent_ids[0]
            print(f"🔼 [RAPTOR] Level 1 Chunk Created: {new_parent_id[:8]}")
            
            # 3. 递归聚类：复用星系重心向量，开启更高层级的知识演化
            clusters = await self._fetch_all_clusters()
            this_cluster = next((c for c in clusters if c["record_id"] == cluster_rec_id), None)
            if this_cluster and this_cluster.get("centroid_embedding"):
                parent_chunk["embedding"] = this_cluster["centroid_embedding"]
                await self.assign_chunk(new_parent_id, parent_chunk)

    async def _create_cluster(self, chunk_data: Dict, vector: List[float]) -> str:
        # 处理 Bitable 复合标签
        raw_tags = chunk_data.get("logic_tags") or ["Misc"]
        normalized_tags = [t.get("text") if isinstance(t, dict) else str(t) for t in raw_tags]
        
        tag_name = normalized_tags[0]
        name = f"Galaxy_{tag_name.title().replace(' ', '_')}"
        
        gal_table = self.store.tables["galaxies"]

        #  物理确权：使用中文确权字段名，防止 FieldNameNotFound
        payload = {"fields": {
            "星系名称": name,
            "锚点关键词": normalized_tags[0], # 物理对齐：API 侧为 select 单选
            "成员总数": 0,
            "重心向量": json.dumps(vector),
            "描述": "自动演化领地"
        }}

        app_token = self.store.app_token
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{gal_table['id']}/records"
        resp = await self.store._api_request("POST", url, payload)
        return resp.get("data", {}).get("record", {}).get("record_id")

    async def _fetch_all_clusters(self) -> List[Dict]:
        gal_table = self.store.tables["galaxies"]
        app_token = self.store.app_token
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{gal_table['id']}/records"
        resp = await self.store._api_request("GET", url)
        items = resp.get("data", {}).get("items", [])
        
        results = []
        for it in items:
            f = it.get("fields", {})
            vec_str = f.get("重心向量", "[]")
            try:
                vec = json.loads(vec_str) if isinstance(vec_str, str) and vec_str != "[]" else vec_str
            except: vec = []
            results.append({"record_id": it["record_id"], "centroid_embedding": vec})
        return results

    async def _link_to_cluster(self, chunk_id: str, cluster_id: str, vector: List[float]):
        app_token = self.store.app_token
        chunk_table_id = self.store.tables["chunks"]["id"]
        
        #  物理确权：使用中文确权字段名，解决 null 写入问题
        payload = {"fields": {
            "星系关联": [cluster_id], 
            "向量表征": json.dumps(vector)
        }}
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{chunk_table_id}/records/{chunk_id}"
        await self.store._api_request("PUT", url, payload)
        await self._evolve_centroid(cluster_id, vector)

    async def _evolve_centroid(self, cluster_id: str, new_vector: List[float]):
        gal_table = self.store.tables["galaxies"]
        app_token = self.store.app_token
        
        url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{gal_table['id']}/records/{cluster_id}"
        resp = await self.store._api_request("GET", url)
        fields = resp.get("data", {}).get("record", {}).get("fields", {})
        
        #  物理确权：强制进行类型转换，防止 Bitable 返回字符串导致的崩溃
        try:
            count = int(fields.get("成员总数", 0))
        except (ValueError, TypeError):
            count = 0
            
        new_count = count + 1
        
        vec_str = fields.get("重心向量", "[]")
        try:
            old_vec = np.array(json.loads(vec_str)) if isinstance(vec_str, str) and vec_str != "[]" else None
        except: old_vec = None
        
        update_fields = {"成员总数": new_count}
        if old_vec is not None and len(old_vec) == len(new_vector):
            updated_vec = (old_vec * count + np.array(new_vector)) / new_count
            update_fields["重心向量"] = json.dumps(updated_vec.tolist())
        else:
            update_fields["重心向量"] = json.dumps(new_vector)

        await self.store._api_request("PUT", url, {"fields": update_fields})
        print(f"🧬 [Evolution] Galaxy {cluster_id[:8]} updated ({new_count})")

cluster_engine = ClusterEngine()
