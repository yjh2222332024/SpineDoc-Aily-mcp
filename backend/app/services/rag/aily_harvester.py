"""
SpineDoc Aily 云端收割机 (AilyHarvester) - V1.0
==============================================
职责：完全解耦本地算力，通过 Aily 实现“语义撞击”，并结合 Bitable 标签实现混合召回。
架构：回归 Phase 1 云端原生设计，整合本地 EvidenceHarvester 的 RRF 排名融合思想。
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
import logging
from backend.app.services.feishu.aily_bridge import aily_bridge
from backend.app.services.feishu.bitable_ledger import bitable_ledger
from backend.app.services.keyword_extractor import get_keyword_extractor
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class AilyHarvester:
    """
    🚀 [V60.0] Aily 云端收割机：SpineDoc 进军飞书生态的‘核心武器’。
    """
    def __init__(self):
        self.extractor = get_keyword_extractor()
        self.rrf_k = 60 # SOTA 常数
        self.W_AILY = 0.6
        self.W_TAGS = 0.3

    async def harvest(self, 
                      query: str, 
                      doc_record_id: Optional[str] = None, 
                      limit: int = 10) -> List[Dict]:
        """
        🚀 核心逻辑：标准双路并行 RRF 融合
        """
        print(f"📡 [AilyHarvester] 启动双路并行收割: {query[:20]}...")

        # 1. 提取关键词
        query_tags = self.extractor.extract_keywords(query, top_n=5)
        
        # 2. 【并行质询】双路并发请求
        tasks = [
            aily_bridge.ask_knowledge(query),
            bitable_ledger.search_chunks(query, doc_record_id=doc_record_id, tags=query_tags, limit=limit * 2)
        ]
        # 等待两路结果同时归位
        vector_results, tag_results = await asyncio.gather(*tasks)
        
        # 3. 【排名熔炼】建立融合字典
        # 这里的 key 是 record_id，这是连接两路的唯一桥梁
        fused_scores = {} # Dict[str, float]
        id_to_data = {}   # 保存原始数据
        
        # --- 路径 A: 向量语义排名 (Weight: 0.6) ---
        for rank, hit in enumerate(vector_results, 1):
            rid = hit.get("id")
            if not rid: continue
            
            # 计算 RRF 分贡献：W / (k + rank)
            score = self.W_AILY / (self.rrf_k + rank)
            fused_scores[rid] = fused_scores.get(rid, 0.0) + score
            id_to_data[rid] = hit
            id_to_data[rid]["found_by_vector"] = True

        # --- 路径 B: 标签逻辑排名 (Weight: 0.3) ---
        for rank, hit in enumerate(tag_results, 1):
            rid = hit.get("id")
            if not rid: continue
            
            # 计算 RRF 分贡献并累加
            score = self.W_TAGS / (self.rrf_k + rank)
            fused_scores[rid] = fused_scores.get(rid, 0.0) + score
            
            # 如果这一路发现了新 ID，存入数据；如果已存在，则保留（通常向量路数据更肥）
            if rid not in id_to_data:
                id_to_data[rid] = hit
            id_to_data[rid]["found_by_tags"] = True

        # 4. 【最终判决】按融合后的总分重排
        final_list = []
        for rid, total_score in fused_scores.items():
            item = id_to_data[rid]
            item["rrf_score"] = total_score
            final_list.append(item)
            
        final_list.sort(key=lambda x: x["rrf_score"], reverse=True)
        
        print(f"✅ [AilyHarvester] RRF 融合完成。Top-1 Score: {final_list[0]['rrf_score'] if final_list else 0:.5f}")
        return final_list[:limit]



aily_harvester = AilyHarvester()
