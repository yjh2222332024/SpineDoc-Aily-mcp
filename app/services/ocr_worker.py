"""
SpineDoc 视觉工作者 (V17.1 单页快速版)
========================================
架构级修复：
1. 放弃批量推理 - RapidOCR 不支持真批量
2. 单页快速推理 - 减少数据拷贝
3. 并行流水线 - CPU 渲染与 GPU 识别并行
"""

import numpy as np
import asyncio
import gc
import logging
import time
from typing import List, Dict, Any, Optional
import fitz
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

_GLOBAL_RAPID_OCR = None


class OCRWorker:
    """
    SpineDoc 视觉工作者 V17.1 - 单页快速版
    
    核心特性:
    - 单页推理：避免批量带来的数据拷贝
    - 预处理优化：原地转换，减少内存分配
    - GPU 锁定：强制 CUDA 加速
    """
    
    def __init__(self, use_gpu: bool = True):
        self.use_gpu = use_gpu
        self._init_engine()

    def _init_engine(self):
        """初始化单引擎 (强制锁定 GPU)"""
        global _GLOBAL_RAPID_OCR

        if _GLOBAL_RAPID_OCR is None:
            from rapidocr_onnxruntime import RapidOCR
            import onnxruntime as ort
            
            print(f"⚙️ [GPU-Lock] 正在强制锁定 GPU 加速...", flush=True)

            providers = [
                ('CUDAExecutionProvider', {
                    'device_id': 0,
                    'gpu_mem_limit': 4 * 1024 * 1024 * 1024,
                    'arena_extend_strategy': 'kSameAsRequested',
                    'do_copy_in_default_stream': True,
                })
            ]

            try:
                available = ort.get_available_providers()
                if 'CUDAExecutionProvider' not in available:
                    raise RuntimeError(f"CRITICAL: CUDAExecutionProvider 未发现，当前可用：{available}")

                _GLOBAL_RAPID_OCR = RapidOCR(providers=providers)

                # 预热
                dummy = np.zeros((100, 100, 3), dtype=np.uint8)
                _GLOBAL_RAPID_OCR(dummy)
                print(f"   ✅ GPU 核心已锁定", flush=True)
            except Exception as e:
                print(f"🚨 [FATAL] GPU 硬件握手失败：{e}", flush=True)
                raise SystemError("GPU Acceleration Required but not available.")

    async def ocr_page_fast(self, img_gray: np.ndarray) -> List[Dict[str, Any]]:
        """
        🆕 单页快速 OCR (V17.1 优化版)
        
        核心优化:
        1. 输入直接是灰度图 (H, W)
        2. 原地转 3 通道，避免额外分配
        3. 直接推理，减少中间层
        """
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, self._ocr_page_fast_sync, img_gray)
        return result

    def _ocr_page_fast_sync(self, img_gray: np.ndarray) -> List[Dict[str, Any]]:
        """同步单页 OCR"""
        global _GLOBAL_RAPID_OCR
        
        # 快速路径：直接转 3 通道
        if len(img_gray.shape) == 2:
            # 使用 np.dstack 比 stack 更快
            img_3ch = np.dstack([img_gray, img_gray, img_gray])
        else:
            img_3ch = img_gray
        
        # 确保 contiguous 内存布局
        if not img_3ch.flags['C_CONTIGUOUS']:
            img_3ch = np.ascontiguousarray(img_3ch)
        
        # 直接推理
        output, _ = _GLOBAL_RAPID_OCR(img_3ch)
        
        # 解析结果
        results = [
            {"text": l[1], "confidence": float(l[2]), "bbox": l[0]}
            for l in output
        ] if output else []
        
        return results

    async def ocr_batch_async(self, images: List[np.ndarray]) -> List[List[Dict[str, Any]]]:
        """
        批量 OCR (V17.1: 并行执行)
        
        🆕 核心优化:
        - 使用 asyncio.gather 并行执行
        - 每页独立推理，避免批量开销
        """
        if not images:
            return []
        
        # 🆕 并行执行：创建所有任务，同时执行
        tasks = [self.ocr_page_fast(img) for img in images]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理异常
        final_results = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.warning(f"⚠️ [OCR] 第{i}页失败：{res}")
                final_results.append([])
            else:
                final_results.append(res)
        
        return final_results

    async def ocr_page_async(self, page: fitz.Page, use_cloud: bool = False) -> List[Dict[str, Any]]:
        """单页 OCR 识别 (兼容旧接口)"""
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), colorspace=fitz.csGRAY)
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w)
        del pix
        
        return await self.ocr_page_fast(img_np)
