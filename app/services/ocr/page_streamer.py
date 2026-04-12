import fitz
import asyncio
import cv2
import numpy as np
from typing import List, Dict, Any, Optional
from .ocr_process_utils import render_page_standard

class PageStreamer:
    """
    🚀 V44.0 流式渲染器
    职责：仅负责按需读取 PDF 页面，将图片喂给队列。利用队列满载机制实现自然反压。
    """
    def __init__(self, file_path: str, scale: float = 1.2):
        self.file_path = file_path
        self.scale = scale

    async def stream_pages(self, target_pages: List[int], queue: asyncio.Queue):
        """流式生产图片数据"""
        from concurrent.futures import ProcessPoolExecutor
        loop = asyncio.get_running_loop()
        
        # 限制渲染进程数，防止多进程同时 load 导致 Malloc
        with ProcessPoolExecutor(max_workers=2) as executor:
            for idx in target_pages:
                # 阻塞式生产：如果队列满了，会自动等待
                p_idx, img_bytes = await loop.run_in_executor(
                    executor, render_page_standard, self.file_path, idx, self.scale
                )
                if img_bytes:
                    await queue.put((p_idx, img_bytes))
        
        # 发送结束信号
        await queue.put(None)
