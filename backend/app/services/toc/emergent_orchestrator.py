"""
SpineDoc 隐性脊梁指挥官 (EmergentSpineOrchestrator) - V3.5
==========================================================
职责：执行“无目录模式”下的逻辑重建。
领域：Table of Contents (TOC) / Implicit Spine Reconstruction (ISR)
核心：从 Level -1 原子分片出发，自下而上蒸馏出隐性逻辑脊梁。
"""

import asyncio
import logging
import uuid
from typing import List, Dict, Any, Optional, Tuple
from backend.app.services.ingestion.splitter import structural_splitter

logger = logging.getLogger(__name__)
from backend.app.services.toc.base import SpineNode

logger = logging.getLogger(__name__)

class EmergentSpineOrchestrator:
    """
     [V3.5] 涌现指挥官：ISR 领域的调度中枢。
    职责：
    1. 驱动全量收割。
    2. 执行三层逻辑蒸馏。
    3. 路径回填与主权对齐。
    """
    def __init__(self):
        self.splitter = structural_splitter

    async def run_full_emergent_pipeline(self, 
                                        doc_id: str, 
                                        filename: str,
                                        doc_obj: Any, 
                                        ocr_context: Optional[Dict[int, str]] = None) -> Tuple[List[Dict], List[SpineNode]]:
        """
         核心：全自动逻辑涌现流水线
        """
        print(f"🌊 [Orchestrator] 启动全自动逻辑涌现流水线: {filename}")

        # 1. 原子收割 (Level -1)
        raw_chunks = await self.harvest_atomic_chunks(doc_obj, ocr_context)
        if not raw_chunks:
            return [], []

        # 2. 逻辑蒸馏 (Building the Pyramid)
        import uuid
        u_doc_id = uuid.UUID(doc_id) if isinstance(doc_id, str) else doc_id
        synthetic_spine = await latent_distiller.distill_emergent_spine(u_doc_id, raw_chunks)

        # 3. 路径回填 (Path Back-filling)
        print(f"🔗 [Orchestrator] 正在执行逻辑主权反哺...")
        self._backfill_breadcrumbs(raw_chunks, synthetic_spine)

        return raw_chunks, synthetic_spine

    async def harvest_atomic_chunks(self, 
                                   doc_obj: Any, 
                                   ocr_context: Optional[Dict[int, str]] = None) -> List[Dict[str, Any]]:
        """
         第一阶段：原子级数据采样
        """
        print(f"📥 [Emergent] 执行暴力全量收割...")
        raw_chunks = []
        async for chunk in self.splitter.split_full_document(doc_obj, ocr_context=ocr_context):
            chunk["level"] = -1
            raw_chunks.append(chunk)
        return raw_chunks

    def _backfill_breadcrumbs(self, chunks: List[Dict], spine: List[SpineNode]):
        """
        根据物理页码，将最深层级的合成标题填入 breadcrumb
        """
        # 按照层级深度排序（-2 比 -3 更深）
        sorted_spine = sorted(spine, key=lambda x: x.level, reverse=True) 

        for c in chunks:
            p_num = c.get("page_number", 0)
            path = []

            # 查找覆盖该页面的所有节点
            # 先找 Level -3 (大章)
            l3_node = next((n for n in sorted_spine if n.level == -3 and n.physical_start <= p_num <= n.physical_end), None)
            if l3_node: path.append(l3_node.title)

            # 再找 Level -2 (子章)
            l2_node = next((n for n in sorted_spine if n.level == -2 and n.physical_start <= p_num <= n.physical_end), None)
            if l2_node: path.append(l2_node.title)

            c["breadcrumb"] = " -> ".join(path) if path else "[Unclassified]"


emergent_orchestrator = EmergentSpineOrchestrator()
