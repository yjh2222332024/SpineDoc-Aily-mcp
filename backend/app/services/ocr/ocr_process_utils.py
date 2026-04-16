import fitz
import os
import socket
import numpy as np
from typing import Optional, Any, Tuple, Dict, List
from pathlib import Path
from dotenv import load_dotenv
import asyncio

# 🏛️ 顶级架构师：统一路径锚定，防止平行宇宙 import
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
import sys
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# 🚀 统一使用标准路径导入

from backend.app.services.ocr.silicon_worker import SiliconVLMWorker
from backend.app.services.ocr.paddle_worker import PaddleWorker
from backend.app.services.ocr.got_worker import GOTWorker
from backend.app.core.config import settings

# 🚀 [V1.2.3] 强制定位项目根目录下的 .env
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path, override=True)

def render_page_standard(pdf_path: str, page_idx: int, scale: float = 1.5):
    try:
        doc = fitz.open(pdf_path)
        page = doc[page_idx]
        pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
        img_bytes = pix.tobytes("jpg")
        doc.close()
        return page_idx, img_bytes
    except Exception as e:
        print(f"❌ [Render] 页面 P{page_idx+1} 渲染失败：{e}")
        return page_idx, None

class AdaptiveOCRWorker:
    """
    🚀 [V1.8.0] GOT 驱动的确定性自适应 OCR 工作器 (纯净版)
    
    策略:
    1. 确定性优先: 使用 PaddleOCR (嗅探) + GOT-OCR 2.0 (精修) 组合。
    2. 高精度 VLM 分流: 目录页专用。
  
    """
    def __init__(self):
        self.paddle_worker: Optional[PaddleWorker] = None
        self.got_worker: Optional[GOTWorker] = None
       
        self.vlm_worker: Optional[SiliconVLMWorker] = None

        self.failure_count = 0
        self.max_failures = 2
        self.switched_to_cloud = False
        self.vlm_failed = False  # 🚀 [V50.7] VLM 失败标志，防止重复尝试
        self._initialize()
    
    def _initialize(self):
        """初始化视觉专家集群"""
        # 1. 🚀 [V1.8.0] 加载确定性感知兵 (Paddle + GOT)
        try:
            self.paddle_worker = PaddleWorker()
            self.got_worker = GOTWorker()
            print("🛡️ [OCR] 确定性感知链 (Paddle + GOT-OCR 2.0) 已就绪")
        except Exception as e:
            print(f"⚠️ [OCR] GOT 感知链加载失败: {e}")

        # 2. 初始化目录专用 VLM
        vlm_key = settings.EMBEDDING_API_KEY
        if vlm_key:
            self.vlm_worker = SiliconVLMWorker(
                api_key=vlm_key,
                base_url=settings.VLM_BASE_URL or "https://api.siliconflow.cn/v1",
                model_name=settings.VLM_MODEL_NAME or "Qwen/Qwen2.5-VL-72B-Instruct"
            )
            print("👁️ [OCR] 高精度 VLM (SiliconFlow) 已就绪")
    
   
    
    async def ocr_to_markdown(self, img_np: np.ndarray, high_precision: bool = False) -> Optional[str]:
        """
        确定性 OCR 识别主入口 (V1.8.0: 纯净并发版)
        """
        # 1. 目录页路径（仅在 VLM 未失败时尝试）
        if high_precision and self.vlm_worker and not self.vlm_failed:
            try:
                result = await self.vlm_worker.ocr_to_markdown(img_np)
                if not result:
                    raise Exception("VLM return empty")
                return result
            except Exception as e:
                self.vlm_failed = True
                return None


        # 2. 🛡️ [V1.8.0] 确定性路径：Paddle (Scout) + GOT (Specialist)
        if self.paddle_worker and self.got_worker and not self.switched_to_cloud:
            try:
                import cv2
                import asyncio
                
                # 🏛️ 嗅探全页
                blocks = await self.paddle_worker.ocr_with_layout(img_np)
                if not blocks: return ""

                loop = asyncio.get_running_loop()
                # 🚀 [V1.8.5] 动态算力配额：从配置层读取并发限制
                semaphore = asyncio.Semaphore(settings.OCR_MAX_CONCURRENCY) 

                async def _process_block(idx: int, b: Dict[str, Any]) -> Tuple[int, str]:
                    is_complex = b['type'] == 'formula' or b['confidence'] < 0.6
                    
                    if is_complex and self.got_worker:
                        async with semaphore:
                            pts = np.array(b['bbox'], dtype=np.int32)
                            x, y, w, h = cv2.boundingRect(pts)
                            padding = 15 
                            crop = img_np[max(0, y-padding):min(img_np.shape[0], y+h+padding), 
                                          max(0, x-padding):min(img_np.shape[1], x+w+padding)]
                            
                            result = await loop.run_in_executor(None, self.got_worker.refine_content, crop)
                            return idx, (result if result else b['text'])
                    else:
                        return idx, b['text']

                tasks = [_process_block(i, b) for i, b in enumerate(blocks)]
                results = await asyncio.gather(*tasks)
                
                # 🏛️ 秩序的胜利：重排序
                results.sort(key=lambda x: x[0])
                
                self.failure_count = 0
                return "\n\n".join([res[1] for res in results])

            except Exception as e:
                print(f"⚠️ [OCR-Pure] 确定性路径失败: {e}")
                self.failure_count += 1
                if self.failure_count >= self.max_failures:
                    self.switched_to_cloud = True
                    self._init_cloud()

        # 3. 唯一的云端回退
        if self.switched_to_cloud and self.cloud_worker:
            return await self.cloud_worker.ocr_to_markdown(img_np)
            
        return None
    
    @property
    def is_cloud(self) -> bool:
        return self.switched_to_cloud
    
    @property
    def available(self) -> bool:
        return (self.paddle_worker is not None and self.got_worker is not None) or \
               self.cloud_worker is not None

def purge_vram():
    import gc
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except: pass
    gc.collect()

# 🏛️ 全局单例缓存，防止重复加载模型导致 OOM (Operation: Unified Brain)
_GLOBAL_OCR_WORKER: Optional['AdaptiveOCRWorker'] = None
_WORKER_LOCK = asyncio.Lock()

async def get_adaptive_ocr_worker():
    """
    🚀 [V1.8.2] 架构师指令：全系统共享唯一感知大脑
    """
    global _GLOBAL_OCR_WORKER
    async with _WORKER_LOCK:
        if _GLOBAL_OCR_WORKER is None:
            # 加载前清理战场
            purge_vram()
            _GLOBAL_OCR_WORKER = AdaptiveOCRWorker()
        return _GLOBAL_OCR_WORKER
