import fitz
import numpy as np
import re
from typing import Dict, Any, List, Tuple
import cv2

# 进程内全局缓存，确保每个进程只加载一次 OCR 模型
_worker_cache = {}

def init_worker(engine_type: str, use_gpu: bool = True):
    """进程初始化函数：在 ProcessPoolExecutor 启动时调用"""
    try:
        from app.services.ocr_worker import OCRWorker
        _worker_cache['worker'] = OCRWorker(engine_type=engine_type, use_gpu=use_gpu)
    except Exception as e:
        print(f"ERROR: Failed to initialize OCR worker process: {e}")

def sniff_worker_static(img_data: Tuple[int, bytes], engine_type: str = "rapid", use_gpu: bool = True) -> Dict[str, Any]:
    """
    极速嗅探子进程逻辑 - 使用 JPEG 压缩图像
    
    Args:
        img_data: (page_idx, jpeg_bytes)
    """
    try:
        page_idx, jpeg_bytes = img_data
        
        # 从 JPEG bytes 解码图像
        img_np = cv2.imdecode(np.frombuffer(jpeg_bytes, dtype=np.uint8), cv2.IMREAD_COLOR)
        
        if img_np is None:
            return {"page_idx": page_idx, "is_anchor": False, "error": "Failed to decode JPEG"}
        
        # 使用预热好的全局单例模型
        worker = _worker_cache.get('worker')
        if not worker:
            from app.services.ocr_worker import OCRWorker
            worker = OCRWorker(engine_type=engine_type, use_gpu=use_gpu)
            _worker_cache['worker'] = worker

        # 执行识别
        raw_results = worker.ocr_page_from_np(img_np)
        text = " ".join([r["text"] for r in raw_results])

        # 特征匹配
        has_toc_keyword = "目录" in text or "Contents" in text or "Table of" in text or "目 录" in text
        has_lu_and_chapters = "录" in text and ("第" in text and "章" in text)
        num_density = len(re.findall(r"\d{1,3}\s*$", text, re.M))
        has_chapter_pattern = len(re.findall(r"第 [一二三四五六七八九十\d]+[章节]", text)) >= 2

        is_anchor = has_toc_keyword or has_lu_and_chapters or has_chapter_pattern or num_density >= 5

        return {
            "page_idx": page_idx,
            "is_anchor": is_anchor,
            "text_preview": text[:50] if text else "EMPTY",
            "debug": {
                "has_toc_keyword": has_toc_keyword,
                "has_lu_and_chapters": has_lu_and_chapters,
                "has_chapter_pattern": has_chapter_pattern,
                "num_density": num_density
            }
        }
    except Exception as e:
        import traceback
        return {"page_idx": -1, "is_anchor": False, "error": str(e) + "\n" + traceback.format_exc()}

def high_precision_worker_static(file_path: str, page_idx: int, engine_type: str = "rapid") -> List[Dict[str, Any]]:
    """高精度提取子进程逻辑"""
    try:
        doc = fitz.open(file_path)
        page = doc[page_idx]
        
        worker = _worker_cache.get('worker')
        if not worker:
            from app.services.ocr_worker import OCRWorker
            worker = OCRWorker(engine_type=engine_type)
            _worker_cache['worker'] = worker
        
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img_np = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
        
        results = worker.ocr_page_from_np(img_np)
        doc.close()
        return results
    except:
        return []
