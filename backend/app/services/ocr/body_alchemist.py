import fitz
import asyncio
import numpy as np
import time
import os
import gc
import cv2
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor
from .ocr_process_utils import render_page_standard, get_adaptive_ocr_worker, AdaptiveOCRWorker
from .zhipu_worker import ZhipuCloudWorker
from .page_streamer import PageStreamer

class BodyAlchemist:
    """
    BodyAlchemist V44.4 - 零驻留流水线模式
    职责：彻底移除了全量内存缓存，OCR 结果直接落盘，内存消耗锁定在 O(1)。
    """
    def __init__(self, concurrent_limit: int = 16):
        self.worker: Optional[AdaptiveOCRWorker] = None
        self.queue = asyncio.Queue(maxsize=4)

    async def _ensure_worker(self):
        if self.worker is None:
            self.worker = await get_adaptive_ocr_worker()
        return self.worker

    async def _ocr_consumer(self, checkpoint_path: str):
        """消费者：处理 OCR 并实时追加至磁盘缓存"""
        worker = await self._ensure_worker()
        while True:
            item = await self.queue.get()
            if item is None:
                self.queue.task_done()
                break
            
            page_idx, img_bytes = item
            print(f"🕵️ [Consumer] 处理 P{page_idx+1}...")
            
            try:
                if worker is None or not worker.available:
                    raise RuntimeError("OCR Worker 不可用")
                
                if img_bytes:
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    markdown = await worker.ocr_to_markdown(img_np)
                    
                    # 🚀 [V44.6] 强力降噪
                    markdown = re.sub(r'【页码：P\d+】', '', markdown)
                    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
                    
                    # 🚀 [V44.4] 即时落盘
                    data = self._load_checkpoint(checkpoint_path)
                    data[str(page_idx)] = markdown
                    self._save_checkpoint(checkpoint_path, data)
                    
                    import torch
                    if torch.cuda.is_available(): torch.cuda.empty_cache()
                    
                    if isinstance(worker, ZhipuCloudWorker):
                        import random
                        await asyncio.sleep(2.0 + random.random() * 1.5)
                else:
                    print(f"⚠️ [Consumer] P{page_idx+1} 数据为空，跳过")

            except Exception as e:
                print(f"🚨 [Consumer] P{page_idx+1} 致命异常: {e}")
            finally:
                self.queue.task_done()

    async def run_full_pipeline(self, file_path: str, toc_items: List[Dict[str, Any]],
                                total_pages: int, router: Any = None,
                                limit_pages: Optional[int] = None) -> Tuple[List[Dict[str, Any]], Dict[int, str]]:
        # 🚀 [V45.2] 强制硬限制：如果 limit_pages 存在，必须在所有逻辑前截断
        if limit_pages and limit_pages < total_pages:
            total_pages = limit_pages
            print(f"🛑 [Pipeline] 强制截断流水线，仅处理前 {total_pages} 页")
            
        checkpoint_path = f"{file_path}.ocr_cache.json"
        
        # 🚀 [V44.4] 无状态化：仅加载进度，不缓存全文
        page_markdowns = self._load_checkpoint(checkpoint_path)
        
        target_pages = self._collect_target_pages(toc_items, total_pages)
        if not target_pages: target_pages = list(range(total_pages))
        target_pages = [p for p in target_pages if str(p) not in page_markdowns]
        if not target_pages: return toc_items, {int(k): v for k, v in page_markdowns.items()}

        self.queue = asyncio.Queue(maxsize=4)
        streamer = PageStreamer(file_path, scale=1.2)
        
        worker = await self._ensure_worker()
        n_consumers = 1 if (worker and worker.is_cloud) else 4
        
        # 启动生产者与消费者
        consumers = [asyncio.create_task(self._ocr_consumer(checkpoint_path)) for _ in range(n_consumers)]
        producer = asyncio.create_task(streamer.stream_pages(target_pages, self.queue))
        
        await producer
        for _ in range(n_consumers): await self.queue.put(None)
        await asyncio.gather(*consumers)
        
        return toc_items, {int(k): v for k, v in self._load_checkpoint(checkpoint_path).items()}

    def _load_checkpoint(self, path: str) -> Dict[str, str]:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: return json.load(f)
            except: pass
        return {}

    def _save_checkpoint(self, path, data):
        try:
            with open(path, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False)
        except: pass

    def _collect_target_pages(self, toc_items: List[Dict], total_pages: int) -> List[int]:
        if not toc_items: return []
        target_pages = []
        sorted_toc = sorted(toc_items, key=lambda x: x["page"])
        for i, it in enumerate(sorted_toc):
            start = it["page"]
            next_start = sorted_toc[i+1]["page"] if i+1 < len(sorted_toc) else total_pages + 1
            for p in range(start, next_start):
                if p <= total_pages: target_pages.append(p - 1)
        return target_pages
