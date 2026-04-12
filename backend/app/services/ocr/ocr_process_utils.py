import fitz
import os
import socket
from typing import Optional, Any, Tuple
from pathlib import Path
from dotenv import load_dotenv
from .glm_worker import GLMWorker
from .zhipu_worker import ZhipuCloudWorker
from .silicon_worker import SiliconVLMWorker
from backend.app.core.config import settings

# 🚀 [V1.2.3] 强制定位项目根目录下的 .env
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
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
    🚀 [V1.4.0] 增强型自适应 OCR 工作器 - 支持高精度 VLM 分流
    
    策略:
    1. 高精度模式 (High Precision): 专门处理目录，走 SiliconFlow Qwen2.5-VL。
    2. 默认模式: 优先本地 GLM-OCR，失败切换云端 Zhipu。
    """
    def __init__(self):
        self.local_worker: Optional[GLMWorker] = None
        self.cloud_worker: Optional[ZhipuCloudWorker] = None
        self.vlm_worker: Optional[SiliconVLMWorker] = None
        self.failure_count = 0
        self.max_failures = 2
        self.switched_to_cloud = False
        self._initialize()
    
    def _initialize(self):
        """初始化视觉专家集群"""
        # 1. 初始化高精度 VLM
        vlm_key = settings.EMBEDDING_API_KEY # 🚀 共享 SiliconFlow Key
        if vlm_key:
            self.vlm_worker = SiliconVLMWorker(
                api_key=vlm_key,
                base_url=settings.VLM_BASE_URL or "https://api.siliconflow.cn/v1",
                model_name=settings.VLM_MODEL_NAME or "Qwen/Qwen2.5-VL-7B-Instruct"
            )
            print("👁️ [OCR] 高精度 VLM (SiliconFlow) 已就绪")

        # 2. 初始化本地 GLM
        try:
            with socket.create_connection(("127.0.0.1", 30000), timeout=0.3):
                self.local_worker = GLMWorker()
                print("🔧 [OCR] 本地 GLM-OCR 已就绪 (SGLang @ 30000)")
        except:
            print("⚠️ [OCR] 本地 SGLang 不可用，正文识别将退守云端")
            self._init_cloud()
    
    def _init_cloud(self):
        zhipu_key = os.getenv("ZHIPU_API_KEY")
        if zhipu_key:
            self.cloud_worker = ZhipuCloudWorker(api_key=zhipu_key)
            print("☁️ [OCR] 云端 Zhipu-OCR 已就绪")
    
    async def ocr_to_markdown(self, img_np, high_precision: bool = False) -> Optional[str]:
        """
        OCR 识别主入口，支持高精度分流
        """
        # 1. 🚀 [V1.4.0] 高精度路径：目录页专用
        if high_precision and self.vlm_worker:
            try:
                return await self.vlm_worker.ocr_to_markdown(img_np)
            except Exception as e:
                print(f"⚠️ [OCR-VLM] 高精度模式失败，尝试退守标准模式: {e}")

        # 2. 标准路径：正文识别
        if self.switched_to_cloud:
            return await self.cloud_worker.ocr_to_markdown(img_np) if self.cloud_worker else None
        
        if self.local_worker:
            try:
                result = await self.local_worker.ocr_to_markdown(img_np)
                self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                if self.failure_count >= self.max_failures:
                    self.switched_to_cloud = True
                    self._init_cloud()
                return await self.ocr_to_markdown(img_np, high_precision=False)
        else:
            return await self.cloud_worker.ocr_to_markdown(img_np) if self.cloud_worker else None
    
    @property
    def is_cloud(self) -> bool:
        return self.switched_to_cloud
    
    @property
    def available(self) -> bool:
        return self.local_worker is not None or self.cloud_worker is not None or self.vlm_worker is not None

def purge_vram():
    import gc
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except: pass
    gc.collect()

async def get_adaptive_ocr_worker():
    return AdaptiveOCRWorker()
