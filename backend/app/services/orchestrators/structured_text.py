from __future__ import annotations
import asyncio
import logging
from pathlib import Path
from uuid import uuid4
from typing import List, Dict, Any, Optional

from backend.app.services.toc.base import SpineNode
from backend.app.core.models import Document
from . import BaseIngestOrchestrator, IngestContext, _finalize_ingestion

logger = logging.getLogger(__name__)

class StructuredTextOrchestrator(BaseIngestOrchestrator):
    """
    StructuredTextOrchestrator: Professional pipeline for Markdown/Text documents.
    Responsibility: Loading, slicing, and initial Bitable persistence.
    """

    def __init__(self, store=None):
        from backend.app.services.feishu.bitable_ledger import bitable_ledger
        self.store = store or bitable_ledger

    async def ingest(self, file_path: str, file_hash: str, engine, ctx: Optional[IngestContext] = None, tag_timeout: int = 300):
        ctx = ctx or IngestContext()
        p = Path(file_path)
        
        # 1. 确权文档记录
        doc_record_id = await self.store.get_or_create_document(
            p.name, file_hash, 1, force=ctx.force
        )

        content_md = ctx.content_md or ""
        is_md = p.suffix.lower() == ".md"

        # 2. 脊梁提取与切片
        physical_toc = self._extract_toc(content_md) if is_md else []
        print(f"📖 [StructuredText] Markdown 激活: {len(physical_toc)} 个节点")

        if physical_toc:
            raw_chunks = await self._slice_by_outline(p.name, physical_toc, content_md)
            synthetic_spine = physical_toc
        else:
            print(f"🌑 [StructuredText] 启动反向涌现模式...")
            raw_chunks = self._emergent_slice(p.name, content_md)
            synthetic_spine = []

        print(f"📦 [StructuredText] 已生成 {len(raw_chunks)} 个分片，准备入库...")
        for i, c in enumerate(raw_chunks[:2]): # 采样日志
             print(f"  ↳ 分片 {i} 预览: {c.get('content', '')[:30]}...")

        # 3. 最终落库编排
        db_doc = Document(filename=p.name, file_hash=file_hash, total_pages=1)

        result = await _finalize_ingestion(
            db_doc, synthetic_spine, raw_chunks, engine,
            skip_bitable=False, store=self.store, tag_timeout=tag_timeout
        )
        print(f"✅ [StructuredText] 落库完成。")
        return result


    def _extract_toc(self, content_md: str) -> list[SpineNode]:
        """从 # 标题提取 TOC"""
        enriched_toc = []
        lines = content_md.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("#"):
                level = line.count("#", 0, line.find(" "))
                if 1 <= level <= 6:
                    enriched_toc.append(SpineNode(
                        level=level,
                        title=line.strip("# ").strip(),
                        logical_page=1, 
                        physical_start=i + 1,
                        source="markdown",
                    ))
        
        for i in range(len(enriched_toc)):
            enriched_toc[i].physical_end = enriched_toc[i+1].physical_start - 1 if i+1 < len(enriched_toc) else len(lines)
        return enriched_toc

    async def _slice_by_outline(self, filename: str, toc: list[SpineNode], content_md: str) -> list:
        lines = content_md.split("\n")
        segments = []
        import hashlib
        for node in toc:
            block = "\n".join(lines[node.physical_start - 1 : node.physical_end]).strip()
            if block:
                # 🚀 物理确权：生成逻辑座标
                logic_coord = f"P{node.logical_page}-{node.physical_start}"
                segments.append({
                    "content": block, 
                    "page_number": node.logical_page, 
                    "breadcrumb": node.title,
                    "logic_coord": logic_coord
                })
        return segments

    def _emergent_slice(self, filename: str, content: str) -> list:
        paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
        import hashlib
        return [{
            "content": p, 
            "page_number": 1, 
            "breadcrumb": filename,
            "logic_coord": f"P1-{hashlib.md5(p.encode()).hexdigest()[:8]}"
        } for p in paragraphs]
