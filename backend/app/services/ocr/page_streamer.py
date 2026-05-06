import fitz
import asyncio
import cv2
import numpy as np
from typing import List, Dict, Any, Optional
from .ocr_process_utils import render_page_standard

class PageStreamer:
    """
     [V44.1] 资源敏感型渲染器
    职责：采用‘瞬时句柄’模式，确保内存中永远只存在一张高清位图。
    """
    def __init__(self, file_path: str, scale: float = 1.2):
        self.file_path = file_path
        self.scale = scale

    async def stream_pages(self, target_pages: List[int], queue: asyncio.Queue):
        """流式生产图片数据 (Operation: Memory Rescue)"""
        import gc
        import time
        
        print(f"🌊 [Streamer] 启动流式收割，目标页数: {len(target_pages)}")
        
        for idx in target_pages:
            try:
                #  只有在真正需要时才调用渲染函数 (内部会 open/close)
                # 我们不再使用进程池，避免 Windows 环境下的内存爆炸
                _, img_bytes = render_page_standard(self.file_path, idx, self.scale)
                
                if img_bytes:
                    # 阻塞式放入队列 (Backpressure)
                    await queue.put((idx, img_bytes))
                    
                #  每一页渲染后强制垃圾回收
                if idx % 5 == 0:
                    gc.collect()
                    
            except Exception as e:
                print(f" [Streamer] P{idx+1} 渲染异常: {e}")
        
        # 发送结束信号
        await queue.put(None)
        print(" [Streamer] 生产线任务分发完毕。")
