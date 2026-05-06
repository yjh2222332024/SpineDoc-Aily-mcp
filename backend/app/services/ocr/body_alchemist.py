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

from .page_streamer import PageStreamer

class BodyAlchemist:
    """
    BodyAlchemist V52.0 - 铁桶阵列落盘版
    职责：引入严格的写锁与周期性(每50页)缓存机制，彻底根除并发覆盖导致的页码丢失问题。
    """
    def __init__(self, concurrent_limit: int = 16):
        self.worker: Optional[AdaptiveOCRWorker] = None
        self.queue = asyncio.Queue(maxsize=4)
        #  [V52.0] 并发防踩踏三剑客
        self._write_lock = asyncio.Lock()
        self._page_buffer = {}
        self._buffer_count = 0

    async def _ensure_worker(self):
        if self.worker is None:
            self.worker = await get_adaptive_ocr_worker()
        return self.worker

    async def _ocr_consumer(self, checkpoint_path: str):
        """消费者：处理 OCR 并周期追加至磁盘缓存"""
        worker = await self._ensure_worker()
        while True:
            item = await self.queue.get()
            if item is None:
                self.queue.task_done()
                break
            
            page_idx, img_bytes = item
            print(f" [Consumer] 处理 P{page_idx+1}...")
            
            try:
                if worker is None or not worker.available:
                    raise RuntimeError("OCR Worker 不可用")
                
                if img_bytes:
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    markdown = await worker.ocr_to_markdown(img_np)
                    
                    #  [V44.6] 强力降噪
                    markdown = re.sub(r'【页码：P\d+】', '', markdown)
                    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
                    
                    #  [V52.0] 周期性并发安全落盘 (聚沙成塔)
                    async with self._write_lock:
                        self._page_buffer[str(page_idx)] = markdown
                        self._buffer_count += 1
                        
                        # 达到 50 页阈值，执行一次原子的合并与保存
                        if self._buffer_count % 50 == 0:
                            print(f" [Checkpoint] 达到 50 页阈值，执行安全合并落盘...")
                            data = self._load_checkpoint(checkpoint_path)
                            data.update(self._page_buffer)
                            self._save_checkpoint(checkpoint_path, data)
                            self._page_buffer.clear() # 清空缓冲
                            
                            # 显存心跳级回收
                            import torch
                            gc.collect()
                            if torch.cuda.is_available(): torch.cuda.empty_cache()
                    
                    
                else:
                    print(f" [Consumer] P{page_idx+1} 数据为空，跳过")

            except Exception as e:
                print(f"🚨 [Consumer] P{page_idx+1} 致命异常: {e}")
            finally:
                self.queue.task_done()

    async def run_full_pipeline(self, file_path: str, toc_items: List[Dict[str, Any]],
                                total_pages: int, router: Any = None,
                                limit_pages: Optional[int] = None,
                                skip_pages: Optional[List[int]] = None,
                                force_ocr: bool = False) -> Tuple[List[Dict[str, Any]], Dict[int, str]]:
        #  [V50.3] 生产级断点续传模式
        if limit_pages and limit_pages < total_pages:
            total_pages = limit_pages
            print(f"🛑 [Pipeline] 强制截断流水线，仅处理前 {total_pages} 页")
            
        checkpoint_path = f"{file_path}.ocr_cache.json"
        page_markdowns = self._load_checkpoint(checkpoint_path)
        
        target_pages = self._collect_target_pages(toc_items, total_pages)
        if not target_pages: target_pages = list(range(total_pages))
        
        #  [V48.0] TOC Bypass
        if skip_pages:
            target_pages = [p for p in target_pages if (p + 1) not in skip_pages]
            
        #  [V50.3] 断点续传
        if not force_ocr:
            already_done = [p for p in target_pages if str(p) in page_markdowns]
            if already_done:
                print(f" [Resumption] 发现磁盘存档！自动跳过 {len(already_done)} 个已处理物理页。")
                target_pages = [p for p in target_pages if str(p) not in page_markdowns]

        if not target_pages:
            print(" [Resumption] 完美！所有页面已在存档中，收割结束。")
            return toc_items, {int(k): v for k, v in page_markdowns.items()}

        self.queue = asyncio.Queue(maxsize=4)
        streamer = PageStreamer(file_path, scale=1.2)
        
        worker = await self._ensure_worker()
        n_consumers = 1 if (worker and worker.is_cloud) else 4
        
        print(f" [Pipeline] 启动收割队列：目标 {len(target_pages)} 页 | 算力分配: {n_consumers} 消费者")
        
        # 启动生产者与消费者
        consumers = [asyncio.create_task(self._ocr_consumer(checkpoint_path)) for _ in range(n_consumers)]
        producer = asyncio.create_task(streamer.stream_pages(target_pages, self.queue))
        
        await producer
        for _ in range(n_consumers): await self.queue.put(None)
        await asyncio.gather(*consumers)
        
        #  [V52.0] 最终收尾：将流水线结束后残留的尾巴数据落盘
        async with self._write_lock:
            if self._page_buffer:
                print(f" [Checkpoint] 流水线结束，将剩余 {len(self._page_buffer)} 页数据安全落盘...")
                data = self._load_checkpoint(checkpoint_path)
                data.update(self._page_buffer)
                self._save_checkpoint(checkpoint_path, data)
                self._page_buffer.clear()
        
        import gc, torch
        gc.collect()
        if torch.cuda.is_available(): torch.cuda.empty_cache()
        
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
        
        #  稳健性增强：统一转为 dict 以支持 SpineNode 对象
        toc_dicts = [it.model_dump() if hasattr(it, "model_dump") else it for it in toc_items]
        
        #  对齐脊梁契约：优先使用 logical_page
        def get_p(it): return it.get("logical_page") or it.get("page", 0)
        
        sorted_toc = sorted(toc_dicts, key=get_p)
        for i, it in enumerate(sorted_toc):
            start = get_p(it)
            if start <= 0: continue
            next_start = get_p(sorted_toc[i+1]) if i+1 < len(sorted_toc) else total_pages + 1
            for p in range(start, next_start):
                if p <= total_pages: target_pages.append(p - 1)
        return list(dict.fromkeys(target_pages))
