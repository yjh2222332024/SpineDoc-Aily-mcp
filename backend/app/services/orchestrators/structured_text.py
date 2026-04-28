from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from backend.app.services.toc.base import SpineNode
from backend.app.services.toc.latent_distiller import latent_distiller
from backend.app.core.models import Document, ProcessingStatus

from . import (
    BaseIngestOrchestrator, IngestContext, _finalize_ingestion,
    _check_duplicate_and_commit,
)


class StructuredTextOrchestrator(BaseIngestOrchestrator):
    """Word / Markdown 等结构化文本管道"""

    async def ingest(
        self, file_path, file_hash, session_maker, engine, ctx=None,
    ):
        ctx = ctx or IngestContext()
        p = Path(file_path)

        # --- 去重 ---
        dup = await _check_duplicate_and_commit(
            str(p), file_hash, ctx.force, session_maker,
        )
        if dup:
            print(f"[Pipeline] 跳过已存在文档: {file_hash[:8]}")
            return dup

        content_md = ctx.content_md or ""

        # --- 提取标题大纲 ---
        enriched_toc = self._extract_toc(content_md)

        if enriched_toc:
            refined_chunks = await self._slice_by_outline(
                p.name, enriched_toc, content_md,
            )
        else:
            refined_chunks, enriched_toc = await self._emergent_pipeline(
                p.name, content_md,
            )

        async with session_maker() as session:
            db_doc = Document(
                id=uuid4(), filename=p.name,
                file_path="virtual_path", file_hash=file_hash,
                status=ProcessingStatus.PROCESSING,
                total_pages=1, is_scanned=False, page_offset=0,
            )
            session.add(db_doc)
            await session.commit()
            await session.refresh(db_doc)

        return await _finalize_ingestion(
            db_doc, enriched_toc, refined_chunks, engine,
        )

    # ── 提取大纲 ──

    def _extract_toc(self, content_md: str) -> list[SpineNode]:
        """从 # 标题提取 TOC"""
        enriched_toc = []
        for line in content_md.split("\n"):
            if line.startswith("#"):
                space_idx = line.find(" ")
                if space_idx > 0:
                    level = line.count("#", 0, space_idx)
                    if level > 0:
                        enriched_toc.append(SpineNode(
                            id=uuid4(), level=level,
                            title=line.strip("# ").strip(),
                            logical_page=1, source="markdown",
                        ))
        return enriched_toc

    # ── 按大纲正向切片 ──

    async def _slice_by_outline(
        self, filename: str, toc: list[SpineNode], content_md: str,
    ) -> list:
        """按标题之间的文本切片"""
        lines = content_md.split("\n")
        header_positions = []
        for i, line in enumerate(lines):
            if line.startswith("#"):
                space_idx = line.find(" ")
                if space_idx > 0:
                    level = line.count("#", 0, space_idx)
                    if level > 0:
                        header_positions.append((i, line.strip("# ").strip(), level))

        segments = []
        for idx, (start_line, title, _) in enumerate(header_positions):
            end_line = header_positions[idx + 1][0] if idx + 1 < len(header_positions) else len(lines)
            block = "\n".join(lines[start_line:end_line]).strip()
            if block:
                segments.append({
                    "content": block, "page": 1, "breadcrumb": title,
                })

        if not segments:
            segments = [{"content": content_md, "page": 1, "breadcrumb": filename}]

        return segments

    # ── 隐式脊梁构建 ──

    async def _emergent_pipeline(
        self, filename: str, content_md: str,
    ) -> tuple[list, list[SpineNode]]:
        print(f"[StructuredText] 未检测到标题，启动隐式脊梁构建...")

        chunks_text = self._split_by_paragraphs(content_md)
        raw_segments = [{
            "content": t, "page": 1, "breadcrumb": filename, "level": -1,
        } for t in chunks_text if t.strip()]

        # 🚀 [V74.0] 语义打标交由飞书捷径处理
        refined_chunks = raw_segments

        synthetic_spine = []
        if refined_chunks:
            synthetic_spine = await latent_distiller.distill_emergent_spine(
                uuid4(), refined_chunks,
            )
            self._backfill_breadcrumbs(refined_chunks, synthetic_spine)

        return refined_chunks, synthetic_spine


    # ── 工具方法 ──

    def _split_by_paragraphs(self, content_md: str) -> list[str]:
        paragraphs = []
        current = []
        for line in content_md.split("\n"):
            if line.strip():
                current.append(line)
            else:
                if current:
                    paragraphs.append("\n".join(current))
                    current = []
        if current:
            paragraphs.append("\n".join(current))
        return paragraphs

    def _backfill_breadcrumbs(self, chunks: list, spine: list[SpineNode]):
        sorted_spine = sorted(spine, key=lambda x: x.level, reverse=True)
        for c in chunks:
            path = []
            for node in sorted_spine:
                if node.level <= -2:
                    path.append(node.title)
            c["breadcrumb"] = " -> ".join(path) if path else "[Unclassified]"
