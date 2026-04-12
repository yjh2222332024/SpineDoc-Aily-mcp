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
    🚀 资深架构师：物理区间分割器 (V4.0 语义切片版)
    职责：基于 TOC 逻辑区间 [p_start, p_end] 对文本进行物理切割。
         使用语义切片替代固定字数切分。
    """
    def __init__(self, 
                 chunk_size: int = 1000, 
                 chunk_overlap: int = 150,
                 use_semantic_split: bool = True):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.use_semantic_split = use_semantic_split
        self.semantic_splitter = None
        if use_semantic_split:
            # 🚀 懒加载，避免启动时阻塞
            try:
                self.semantic_splitter = SemanticSplitter(threshold=0.45)
                logger.info("✅ 语义切片器已加载")
            except Exception as e:
                logger.warning(f"⚠️ 语义切片器加载失败，降级为固定字数切分：{e}")
                self.semantic_splitter = None

    def _split_by_semantic(self, text: str, min_chunk_len: int = 300) -> List[str]:
        """
        使用语义切片（优先）
        """
        if self.semantic_splitter is None:
            return self._split_by_fixed_size(text)
        
        try:
            chunks = self.semantic_splitter.split_text(text, min_chunk_len=min_chunk_len)
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
                           ocr_context: Optional[Dict[int, str]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        按 TOC 逻辑区间分片 (V46.6 强类型契约版)
        职责：严格遵循 SpineNode 契约，执行物理区间分片。
        """
        total_items = len(toc_items)
        total_pages = len(doc)

        for idx, item in enumerate(toc_items, 1):
            p_start = item.physical_start
            p_end = item.physical_end
            title = item.title

            # 跳过无效区间
            if p_start > p_end:
                print(f"⚠️ [Splitter] ({idx}/{total_items}) 跳过无效区间：{title} (P{p_start}-P{p_end})")
                continue

            print(f"🧩 [Splitter] ({idx}/{total_items}) 正在处理章节：[bold green]{title}[/bold green] (P{p_start}-P{p_end})")

            # 1. 收集整个章节的文本
            chapter_text = ""
            for p_idx in range(p_start - 1, min(p_end, total_pages)):
                page_tag = f"\n【页码：P{p_idx+1}】\n"
                if ocr_context and p_idx in ocr_context:
                    chapter_text += page_tag + ocr_context[p_idx]
                else:
                    chapter_text += page_tag + doc[p_idx].get_text()

            # 2. 一次性执行语义切分
            print(f"  ↳ 🧠 正在执行章节级语义切分...")
            raw_sub_texts = self._split_by_semantic(chapter_text, min_chunk_len=300)

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
                                  ocr_context: Optional[Dict[int, str]] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        🚀 V4.0 新增：全量文档语义切片（带进度监控）
        """
        total_pages = len(doc)
        buffer_size = 5  # 每 5 页进行一次语义切片
        buffer_text = ""
        buffer_start_page = 1
        
        print(f"🌊 [Splitter] 启动全量语义切片流，共 {total_pages} 页...")
        
        for p_idx in range(total_pages):
            if (p_idx + 1) % 10 == 0:
                print(f"  ↳ 📥 正在读取物理页码: P{p_idx+1}/{total_pages} ({(p_idx+1)/total_pages*100:.1f}%)")
            
            page_tag = f"\n【页码：P{p_idx+1}】\n"
            if ocr_context and p_idx in ocr_context:
                buffer_text += page_tag + ocr_context[p_idx]
            else:
                buffer_text += page_tag + doc[p_idx].get_text()
            
            # 每 5 页或最后一页，进行语义切片
            if (p_idx + 1) % buffer_size == 0 or (p_idx + 1) == total_pages:
                if buffer_text:
                    chunks = self._split_by_semantic(buffer_text, min_chunk_len=300)
                    
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
                                "split_method": "semantic" if self.semantic_splitter else "fixed_size"
                            }
                        }
                
                buffer_text = ""
                buffer_start_page = p_idx + 2
        print(f"✅ [Splitter] 全量文档切分流水线执行完毕。")


structural_splitter = StructuralSplitter(use_semantic_split=True)
