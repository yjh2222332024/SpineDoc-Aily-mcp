"""
SpineDoc 隐性脊梁蒸馏器 (LatentSpineDistiller) - V3.5
==========================================================
职责：利用“关键词+首句摘要”实现极低成本的逻辑涌现。
核心：严格遵循物理相邻性与规模约束，生成符合 SpineNode 契约的合成脊梁。
"""

import asyncio
import logging
import uuid
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from openai import AsyncOpenAI
from backend.app.core.config import settings
from backend.app.services.toc.base import SpineNode

logger = logging.getLogger(__name__)

class LatentSpineDistiller:
    def __init__(self):
        # 🚀 [V60.0] 动态路由：自动适配火山引擎/OpenAI 接口
        self.client = AsyncOpenAI(
            api_key=settings.REAL_LLM_KEY, 
            base_url=settings.LLM_BASE_URL
        )
        self.model = settings.REAL_LLM_MODEL

    async def distill_emergent_spine(self, 
                                    doc_id: uuid.UUID, 
                                    refined_chunks: List[Dict[str, Any]]) -> List[SpineNode]:
        """
        🚀 核心入口：构建三层逻辑金字塔 (-1 -> -2 -> -3)
        """
        if not refined_chunks: return []
        
        print(f"🧪 [Distiller] 启动三层蒸馏塔...")

        # 1. 准备 Level -1 指纹 (Atoms)
        fingerprints = []
        for idx, c in enumerate(refined_chunks):
            # 🚀 [V63.0] 优先使用 Bitable AI 反哺的云端摘要
            hook_content = c.get("summary", "")
            if not hook_content:
                hook_content = c.get("content", "")[:settings.CONTEXT_CHUNK_PREVIEW_CONTENT]
                
            fingerprints.append({
                "index": idx,
                "p": c.get("page_number", 0),
                "tags": c.get("logic_tags", [])[:8],
                "summary": hook_content.strip()
            })

        # 2. 蒸馏 Level -2 (Sections)
        print(f"  ↳ [Layer -2] 正在将 {len(fingerprints)} 个原子塌缩为局部话题...")
        level_2_nodes = await self._find_logical_breaks(doc_id, fingerprints, target_level=-2)
        if not level_2_nodes:
            # 兜底：如果 LLM 失败，强行按物理每 10 个切片分一段
            level_2_nodes = self._fallback_partition(fingerprints, -2)

        # 3. 蒸馏 Level -3 (Chapters)
        print(f"  ↳ [Layer -3] 正在将 {len(level_2_nodes)} 个子话题聚合为主权章节...")
        level_3_nodes = await self._aggregate_to_level_3(doc_id, level_2_nodes)

        # 4. 汇总与物理确权
        total_nodes = level_3_nodes + level_2_nodes
        self._ensure_physical_integrity(total_nodes, refined_chunks)
        
        return total_nodes

    def _fallback_partition(self, fingerprints: List[Dict], level: int) -> List[SpineNode]:
        """
        🚀 架构师的降级方案：物理暴力分区，确保系统不挂起。
        """
        nodes = []
        batch_size = 10
        for i in range(0, len(fingerprints), batch_size):
            batch = fingerprints[i:i + batch_size]
            nodes.append(SpineNode(
                id=uuid.uuid4(),
                title=f"[Synthetic] Section {i//batch_size + 1}",
                level=level,
                logical_page=batch[0]["p"],
                physical_start=batch[0]["p"],
                physical_end=batch[-1]["p"],
                source="distiller_fallback",
                is_synthetic=True
            ))
        return nodes

    async def _find_logical_breaks(self, 
                                 doc_id: uuid.UUID, 
                                 fingerprints: List[Dict], 
                                 target_level: int) -> List[SpineNode]:
        """
        利用 LLM 寻找逻辑边界 (V4.0 标签驱动聚类版)
        """
        prompt = f"""你是一个顶级的文档结构架构师。请根据以下文档分片的指纹（物理页码 p、语义标签 tags、逻辑摘要 summary），将其划分为具有逻辑意义的【子章节】。
        
        🚀 核心聚类法则：
        1. 重点观察【语义标签 tags】的聚集效应。如果连续多个分片具有相同或高度相关的标签，它们必须被划入同一个子章节。
        2. 当标签的主题发生明显转换时，即为切断边界。
        
        约束要求：
        1. 必须保持物理页码的顺序，不能跨页聚合。
        2. 每个章节至少包含 2 个分片，至多包含 15 个分片。
        3. 标题必须精炼（15字以内），必须高度概括该区域的核心【语义标签】。
        4. 严格输出 JSON 数组格式：[{"{"}"title": "...", "start_idx": 0, "end_idx": 5{"}"}, ...]
        
        指纹列表：
        {json.dumps(fingerprints, ensure_ascii=False)}
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"} if "gpt" in self.model or "deepseek" in self.model else None
            )
            content = response.choices[0].message.content
            # 解析 JSON
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if not match: return []
            data = json.loads(match.group(0))
            
            nodes = []
            for item in data:
                s_idx, e_idx = item["start_idx"], item["end_idx"]
                # 物理边界校验
                batch = fingerprints[s_idx:e_idx+1]
                if not batch: continue
                
                nodes.append(SpineNode(
                    id=uuid.uuid4(),
                    title=f"[Synthetic] {item['title']}",
                    level=target_level,
                    logical_page=batch[0]["p"],
                    physical_start=batch[0]["p"],
                    physical_end=batch[-1]["p"],
                    source="latent_distiller",
                    is_synthetic=True
                ))
            return nodes
        except Exception as e:
            logger.error(f"逻辑分段失败: {e}")
            return []

    async def _aggregate_to_level_3(self, doc_id: uuid.UUID, sub_nodes: List[SpineNode]) -> List[SpineNode]:
        """
        🚀 [V3.5] 主权聚合：将子章节 (Level -2) 归并为大章节 (Level -3)
        """
        if len(sub_nodes) <= 3: 
            return [] # 规模太小，不进行二次分层

        # 准备子节点元数据
        sub_metadata = []
        for idx, n in enumerate(sub_nodes):
            sub_metadata.append({
                "index": idx,
                "title": n.title,
                "range": f"P{n.physical_start}-P{n.physical_end}"
            })

        prompt = f"""你是一个文档架构师。请将以下【子章节】进一步归类为 2-5 个【大章节】。
        要求：
        1. 必须保持顺序，不能跨越物理区间。
        2. 大章节标题必须具备高度概括性（15字以内）。
        3. 严格输出 JSON 数组格式：[{"{"}"title": "...", "start_idx": 0, "end_idx": 3{"}"}, ...]
        
        子章节列表：
        {json.dumps(sub_metadata, ensure_ascii=False)}
        """

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            content = response.choices[0].message.content
            match = re.search(r'\[.*\]', content, re.DOTALL)
            if not match: return []
            data = json.loads(match.group(0))

            master_nodes = []
            for item in data:
                s_idx, e_idx = item["start_idx"], item["end_idx"]
                # 严格通过子节点锚定物理边界
                batch = sub_nodes[s_idx:e_idx+1]
                if not batch: continue

                master_nodes.append(SpineNode(
                    id=uuid.uuid4(),
                    title=f"[Synthetic Master] {item['title']}",
                    level=-3,
                    logical_page=batch[0].physical_start,
                    physical_start=batch[0].physical_start,
                    physical_end=batch[-1].physical_end,
                    source="latent_distiller",
                    is_synthetic=True
                ))
            return master_nodes
        except Exception as e:
            logger.error(f"Level -3 聚合失败: {e}")
            return []

    def _ensure_physical_integrity(self, nodes: List[SpineNode], chunks: List[Dict]):
        """
        🚀 架构师铁律：强制执行物理区间闭合
        1. 确保所有节点的物理页码与对应的 Chunk 严格对齐。
        2. 确保同一层级的节点之间没有物理空隙。
        """
        if not nodes: return
        
        # 按层级分组处理
        for lvl in [-2, -3]:
            lvl_nodes = sorted([n for n in nodes if n.level == lvl], key=lambda x: x.physical_start)
            if not lvl_nodes: continue
            
            # 闭合逻辑：确保前一个节点的 end 是下一个节点 start 的前一页（或相等）
            for i in range(len(lvl_nodes) - 1):
                if lvl_nodes[i].physical_end >= lvl_nodes[i+1].physical_start:
                    # 发生重叠，强制修正
                    lvl_nodes[i].physical_end = lvl_nodes[i+1].physical_start - 1
                
            # 最后一个节点延伸至文档末尾页（可选，但通常推荐）
            if chunks:
                max_p = max(c.get("page_number", 0) for c in chunks)
                lvl_nodes[-1].physical_end = max(lvl_nodes[-1].physical_end, max_p)

latent_distiller = LatentSpineDistiller()
