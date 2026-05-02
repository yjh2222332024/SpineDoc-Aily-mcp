"""
SpineDoc 结构化分片引擎 (V4.0 语义切片版)
========================================
职责：执行物理分割，支持 TOC 结构化分片与全量 Markdown 分片。
     使用语义切片替代固定字数切分，保持语义完整性。
"""
# 🔥 修复 Python 路径问题（Windows 专用）
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent  # 跳到项目根目录
sys.path.append(str(project_root))
import re
import uuid
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from .splitter_semantic import SemanticSplitter
from backend.app.services.toc.base import SpineNode
logger = logging.getLogger(__name__)

class StructuralSplitter:
    """
    🚀 资深架构师：物理区间分割器 (V5.1 Clean Code 版)
    职责：基于 TOC 逻辑区间执行递归结构化切分。
    """
    # 定义层级分隔符，体现 Aily 的结构优先原则
    DEFAULT_SEPARATORS = ["\n\n", "\n", "。", "！", "？", ". ", " "]

    def __init__(self, 
                 chunk_size: int = 800, 
                 chunk_overlap: int = 150,
                 use_semantic_split: bool = False):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_semantic_split = use_semantic_split
        self.semantic_splitter = None
        
        if use_semantic_split:
            self._init_semantic_engine()

    def _init_semantic_engine(self):
        try:
            self.semantic_splitter = SemanticSplitter(threshold=0.45)
            logger.info("✅ 语义切片器已加载")
        except Exception as e:
            logger.warning(f"⚠️ 语义切片器加载失败：{e}")

    async def _split_text_smart(self, text: str) -> List[str]:
        """智能路由：优先使用递归切分，除非显式开启语义黑盒"""
        if self.use_semantic_split and self.semantic_splitter:
            return await self._split_by_semantic(text)
        
        return self._split_recursively(text, self.DEFAULT_SEPARATORS)

    def _split_recursively(self, text: str, separators: List[str]) -> List[str]:
        if len(text) <= self.chunk_size:
            return [text]
        
        separator = self._pick_best_separator(text, separators)
        parts = text.split(separator)
        return self._combine_parts(parts, separator)

    def _pick_best_separator(self, text: str, separators: List[str]) -> str:
        for s in separators:
            if s in text:
                return s
        return separators[-1]

    def _combine_parts(self, parts: List[str], separator: str) -> List[str]:
        chunks = []
        current_chunk = ""
        
        for p in parts:
            if self._is_overflow(current_chunk, p, separator):
                chunks.append(current_chunk)
                current_chunk = self._create_overlap_bridge(current_chunk)
            
            current_chunk = self._add_part_to_chunk(current_chunk, p, separator)
        
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    def _is_overflow(self, current: str, next_part: str, sep: str) -> bool:
        return len(current) + len(next_part) + len(sep) > self.chunk_size and current != ""

    def _add_part_to_chunk(self, current: str, part: str, sep: str) -> str:
        prefix = sep if current and not current.endswith(sep) else ""
        return current + prefix + part

    def _create_overlap_bridge(self, previous_chunk: str) -> str:
        """建立切片间的逻辑桥梁，确保上下文不丢失"""
        if len(previous_chunk) <= self.chunk_overlap:
            return previous_chunk
        return previous_chunk[-self.chunk_overlap:]

    async def _split_by_semantic(self, text: str, min_chunk_len: int = 300) -> List[str]:
        """
        使用语义切片（优先）
        """
        if self.semantic_splitter is None:
            return self._split_by_fixed_size(text)
        
        try:
            # 🚀 补上缺失的 await
            chunks = await self.semantic_splitter.split_text(text, min_chunk_len=min_chunk_len)
            # 过滤太短的 chunk
            return [c for c in chunks if len(c) >= 30]
        except Exception as e:
            logger.warning(f"⚠️ 语义切片失败，降级为固定字数切分：{e}")
            return self._split_by_fixed_size(text)

    def _split_by_fixed_size(self, text: str) -> List[str]:
        """
        固定字数切分（兜底）
        """
        if len(text) <= self.chunk_size:
            return [text]
        
        step = self.chunk_size - self.chunk_overlap
        chunks = []
        for j in range(0, len(text), step):
            chunks.append(text[j:j+self.chunk_size])
        return chunks

    async def split_by_toc(self,
                           doc: Any,
                           toc_items: List[SpineNode],
                           ocr_context: Optional[Dict[int, str]] = None,
                           page_text_map: Optional[Dict[int, str]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        按 TOC 逻辑区间分片 (V5.2 契约修复版)
        职责：严格遵循 SpineNode 契约，优先使用原生文本映射 (page_text_map)。
        """
        total_items = len(toc_items)
        total_pages = len(doc)

        for idx, item in enumerate(toc_items, 1):
            p_start = item.physical_start
            p_end = item.physical_end
            title = item.title

            if p_start > p_end:
                continue

            # 1. 收集整个章节的文本
            chapter_text = ""
            for p_idx in range(p_start - 1, min(p_end, total_pages)):
                page_tag = f"\n【页码：P{p_idx+1}】\n"
                # 优先级：原生文本映射 > OCR 上下文 > PyMuPDF 直接提取
                if page_text_map and p_idx in page_text_map:
                    chapter_text += page_tag + page_text_map[p_idx]
                elif ocr_context and p_idx in ocr_context:
                    chapter_text += page_tag + ocr_context[p_idx]
                else:
                    chapter_text += page_tag + doc[p_idx].get_text()

            # 2. 智能切分
            raw_sub_texts = await self._split_text_smart(chapter_text)

            for sub_text in raw_sub_texts:
                clean_text = sub_text.strip()
                if len(clean_text) < 30:
                    continue

                # 追踪页码：找到文本中最后一个页码标记
                page_matches = re.findall(r'【页码：P(\d+)】', clean_text)
                curr_page = int(page_matches[-1]) if page_matches else p_start

                yield {
                    "id": str(uuid.uuid4()),
                    "content": clean_text,
                    "page_number": curr_page,
                    "breadcrumb": title,
                    "metadata_json": {
                        "p_start": p_start,
                        "p_end": p_end,
                        "toc_title": title,
                        "split_method": "semantic_chapter"
                    }
                }

            # 章节间清理内存
            import gc
            gc.collect()

    async def split_full_document(self,
                                  doc: Any,
                                  ocr_context: Optional[Dict[int, str]] = None,
                                  page_text_map: Optional[Dict[int, str]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        🚀 V4.0 新增：全量文档语义切片（带进度监控）
        """
        total_pages = len(doc)
        buffer_size = 1  # 🚀 [V63.0] 极致精细化：逐页推送，利用 Bitable AI 进行高密度反哺
        buffer_text = ""
        buffer_start_page = 1

        
        print(f"🌊 [Splitter] 启动全量语义切片流，共 {total_pages} 页...")
        
        for p_idx in range(total_pages):
            if (p_idx + 1) % 10 == 0:
                print(f"  ↳ 📥 正在读取物理页码: P{p_idx+1}/{total_pages} ({(p_idx+1)/total_pages*100:.1f}%)")
            
            page_tag = f"\n【页码：P{p_idx+1}】\n"
            # 优先级：原生文本映射 > OCR 上下文 > PyMuPDF 直接提取
            if page_text_map and p_idx in page_text_map:
                buffer_text += page_tag + page_text_map[p_idx]
            elif ocr_context and p_idx in ocr_context:
                buffer_text += page_tag + ocr_context[p_idx]
            else:
                buffer_text += page_tag + doc[p_idx].get_text()
            
            # 每 5 页或最后一页，进行切片
            if (p_idx + 1) % buffer_size == 0 or (p_idx + 1) == total_pages:
                if buffer_text:
                    chunks = await self._split_text_smart(buffer_text)
                    
                    current_page = buffer_start_page
                    for chunk in chunks:
                        clean_chunk = chunk.strip()
                        if len(clean_chunk) < 30: continue
                        
                        # 追踪页码
                        page_matches = re.findall(r'【页码：P(\d+)】', clean_chunk)
                        if page_matches:
                            current_page = int(page_matches[-1])
                        
                        yield {
                            "id": str(uuid.uuid4()),
                            "content": clean_chunk,
                            "page_number": current_page,
                            "breadcrumb": "Full Document",
                            "metadata_json": {
                                "p_start": buffer_start_page,
                                "p_end": p_idx + 1,
                                "toc_title": "Full Document",
                                "split_method": "recursive_structural"
                            }
                        }
                
                buffer_text = ""
                buffer_start_page = p_idx + 2
        print(f"✅ [Splitter] 全量文档切分流水线执行完毕。")


structural_splitter = StructuralSplitter(use_semantic_split=False)
