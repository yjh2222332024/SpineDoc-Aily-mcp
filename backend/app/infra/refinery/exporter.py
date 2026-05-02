"""
⚠️ DEPRECATED - RefineryExporter
====================================
This module is deprecated. Local database persistence has been phased out.
Logical extraction and refinery should now target Feishu Bitable or Git Ledger.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.models import Chunk, ChunkRelationship, ChunkRevision, Document
from backend.app.services.knowledge.git_manager import get_git_manager

logger = logging.getLogger(__name__)

class RefineryExporter:
    """
    负责将联邦法庭的“审判档案”与“演进历史”转化为 1.5B 模型能吸收的灵魂养分。
    """
    def __init__(self, session: AsyncSession):
        self.session = session
        self.git_manager = get_git_manager()

    async def export_logic_crystals(self, output_path: str, format: str = "jsonl"):
        """
        🚀 启动全量结晶导出流程
        """
        print(f"💎 [Refinery] 正在启动逻辑结晶流程，格式: {format}...")
        
        # 1. 提取推理迹 (来自法官判决)
        reasoning_data = await self.export_reasoning_traces()
        
        # 2. 提取知识演进 (来自 Git Ledger)
        evolution_data = await self.export_evolution_pairs()
        
        # 3. 提取网格拓扑 (来自 Knowledge Mesh)
        mesh_data = await self.export_mesh_topologies()
        
        all_crystals = reasoning_data + evolution_data + mesh_data
        
        # 物理落盘
        self._save_to_disk(all_crystals, output_path, format)
        print(f"✅ [Refinery] 导出完成！共计 {len(all_crystals)} 条高压逻辑语料。")

    async def export_reasoning_traces(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        提取带 CoT 的推理迹 (Court Verdicts)
        训练 1.5B 模型内化大法官的辩论与决策逻辑。
        """
        print("   ↳ 正在提纯推理迹 (Court Verdicts)...")
        from backend.app.core.models import RetrievalResult
        stmt = select(RetrievalResult).order_by(RetrievalResult.created_at).limit(limit)
        result = await self.session.execute(stmt)
        verdicts = result.scalars().all()
        
        dataset = []
        for v in verdicts:
            dataset.append({
                "instruction": v.query,
                "thought": v.reasoning_thought, # 存储在大模型裁决阶段的 0.1 度严谨思考
                "answer": v.final_answer,      # 经过外交官润色后的答案（或原始答案）
                "cited_galaxies": v.cited_galaxies,
                "confidence": v.confidence_score,
                "label": "COURT_REASONING_TRACE"
            })
        return dataset

    async def export_evolution_pairs(self) -> List[Dict[str, Any]]:
        """
        提取知识演进对 (Git Ledger)
        训练 1.5B 模型识别并修正“陈旧事实”的能力。
        """
        print("   ↳ 正在提纯知识演进对...")
        stmt = select(ChunkRevision).order_by(ChunkRevision.created_at)
        result = await self.session.execute(stmt)
        revisions = result.scalars().all()
        
        dataset = []
        for rev in revisions:
            # 兼容处理：获取 commit_hash (如果模型中未定义则使用 id 占位)
            commit_id = getattr(rev, "commit_hash", str(rev.id))[:8]
            dataset.append({
                "instruction": f"由于知识代谢，请更新关于 '{rev.change_reason}' 的表述。",
                "old_content": rev.old_content,
                "new_content": rev.new_content,
                "context": f"revision_id: {commit_id}",
                "label": "KNOWLEDGE_EVOLUTION"
            })
        return dataset

    async def export_mesh_topologies(self) -> List[Dict[str, Any]]:
        """
        提取逻辑网格路径 (Knowledge Mesh)
        训练模型对事实关联的敏感度 (Causality/Contradiction)。
        """
        print("   ↳ 正在提纯逻辑网格路径...")
        stmt = select(ChunkRelationship)
        result = await self.session.execute(stmt)
        relations = result.scalars().all()
        
        dataset = []
        for rel in relations:
            # 兼容处理 Enum 类型，提取其纯字符串值
            raw_rel_type = rel.rel_type
            if hasattr(raw_rel_type, "value"):
                rel_type_str = raw_rel_type.value
            else:
                rel_type_str = str(raw_rel_type).split(".")[-1]
            
            dataset.append({
                "instruction": f"分析以下两个事实片段之间的 {rel_type_str} 关系。",
                "chunk_a": str(rel.source_chunk_id),
                "chunk_b": str(rel.target_chunk_id),
                "reasoning": rel.description,
                "label": f"MESH_{rel_type_str.upper()}"
            })
        return dataset

    def _save_to_disk(self, data: List[Dict], path: str, format: str):
        with open(path, "w", encoding="utf-8") as f:
            if format == "jsonl":
                for item in data:
                    f.write(json.dumps(item, ensure_ascii=False) + "\n")
            else:
                json.dump(data, f, ensure_ascii=False, indent=2)
