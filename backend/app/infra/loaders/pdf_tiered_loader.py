import fitz
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from backend.app.core.interfaces.loader import IDocumentLoader

class TieredPdfLoader(IDocumentLoader):
    """
     SpineDoc 智能变速加载器 (V55.0)
    职责：根据文档复杂度自动切换算力档位 (Tier 1-3)。
    """
    
    def __init__(self):
        self.use_gpu = True # 本地 4060 环境开启

    def can_handle(self, path_or_url: str) -> bool:
        return path_or_url.lower().endswith(".pdf")

    def _sniff_complexity(self, path: str) -> int:
        """
         复杂度嗅探器 (Complexity Sniffer)
        返回档位：1 (极速), 2 (综合), 3 (深度/4060)
        """
        doc = fitz.open(path)
        total_pages = len(doc)
        text_density = 0
        table_like_count = 0

        # 采样前 5 页进行嗅探
        for i in range(min(5, total_pages)):
            page = doc[i]
            text = page.get_text()
            text_density += len(text)
            # 嗅探是否有密集的线条（通常代表表格）
            if len(page.get_drawings()) > 20:
                table_like_count += 1
        
        doc.close()

        # 逻辑判决：
        if text_density < 50 and total_pages > 0:
            return 3 # 几乎没文字，判定为扫描件或纯图 -> 走 Docling/GPU
        if table_like_count >= 3:
            return 3 # 发现密集表格 -> 走 Docling 高精度拆解
        return 1 # 标准文档 -> 走 PyMuPDF4LLM

    async def load(self, path_or_url: str) -> str:
        tier = self._sniff_complexity(path_or_url)
        print(f" [TieredLoader] 自动换挡：Tier {tier} 激活")

        if tier == 1:
            import pymupdf4llm
            return pymupdf4llm.to_markdown(path_or_url)
        
        if tier == 2:
            from markitdown import MarkItDown
            md = MarkItDown()
            result = md.convert(path_or_url)
            return result.text_content

        if tier == 3:
            #  激活 4060 重炮：使用 Docling
            # 采用延迟导入，防止启动时就吃掉显存
            print(" [Tier 3] 正在启动 Docling 深度审计引擎 (4060 加速)...")
            from docling.datamodel.base_models import InputFormat
            from docling.document_converter import DocumentConverter
            
            converter = DocumentConverter()
            result = converter.convert(path_or_url)
            return result.document.export_to_markdown()

        return ""
