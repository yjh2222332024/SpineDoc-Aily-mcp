import fitz
import os
import socket
from typing import Optional, Any, Tuple
from pathlib import Path
from dotenv import load_dotenv
from .glm_worker import GLMWorker
from .zhipu_worker import ZhipuCloudWorker

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
    🚀 [V1.3.2] 自适应 OCR 工作器 - 本地优先 + 降级切换
    
    策略:
    1. 优先使用本地 GLM-OCR (SGLang @ 30000 端口)
    2. 连续失败 2 次后自动切换云端 Zhipu OCR
    3. 切换后不再回退
    """
    def __init__(self):
        self.local_worker: Optional[GLMWorker] = None
        self.cloud_worker: Optional[ZhipuCloudWorker] = None
        self.failure_count = 0
        self.max_failures = 2
        self.switched_to_cloud = False
        self._initialize()
    
    def _initialize(self):
        """初始化本地 worker"""
        try:
            with socket.create_connection(("127.0.0.1", 30000), timeout=0.3):
                self.local_worker = GLMWorker()
                print("🔧 [OCR] 本地 GLM-OCR 已就绪 (SGLang @ 30000)")
        except:
            print("⚠️ [OCR] 本地 SGLang 不可用，将直接使用云端 OCR")
            self._init_cloud()
    
    def _init_cloud(self):
        """初始化云端 worker"""
        zhipu_key = os.getenv("ZHIPU_API_KEY")
        if zhipu_key:
            self.cloud_worker = ZhipuCloudWorker(api_key=zhipu_key)
            print("☁️ [OCR] 云端 Zhipu-OCR 已就绪")
        else:
            print("❌ [OCR] 未配置 ZHIPU_API_KEY，OCR 功能不可用")
    
    def _switch_to_cloud(self):
        """切换到云端 OCR"""
        if self.switched_to_cloud:
            return
        
        print(f"\n🔄 [OCR] 本地连续失败{self.max_failures}次，正在切换至云端 OCR...")
        self._init_cloud()
        self.switched_to_cloud = True
        
        if self.cloud_worker is None:
            print("❌ [OCR] 云端切换失败，OCR 功能完全不可用")
    
    async def ocr_to_markdown(self, img_np) -> Optional[str]:
        """
        OCR 识别，带失败降级
        """
        if self.switched_to_cloud:
            if self.cloud_worker is None:
                return None
            try:
                return await self.cloud_worker.ocr_to_markdown(img_np)
            except Exception as e:
                print(f"⚠️ [OCR-Cloud] 识别失败：{e}")
                return None
        
        if self.local_worker:
            try:
                result = await self.local_worker.ocr_to_markdown(img_np)
                self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                print(f"⚠️ [OCR-Local] 失败 ({self.failure_count}/{self.max_failures}): {e}")
                if self.failure_count >= self.max_failures:
                    self._switch_to_cloud()
                    if self.cloud_worker:
                        try:
                            return await self.cloud_worker.ocr_to_markdown(img_np)
                        except Exception as cloud_e:
                            print(f"⚠️ [OCR-Cloud] 重试失败：{cloud_e}")
                            return None
                    return None
                return None
        else:
            if self.cloud_worker:
                try:
                    return await self.cloud_worker.ocr_to_markdown(img_np)
                except Exception as e:
                    print(f"⚠️ [OCR-Cloud] 识别失败：{e}")
                    return None
            return None
    
    @property
    def is_cloud(self) -> bool:
        return self.switched_to_cloud
    
    @property
    def available(self) -> bool:
        return self.local_worker is not None or self.cloud_worker is not None

def purge_vram():
    """🔥 架构师级：强制显存清场，确保 OCR 与 SLM 无缝接力"""
    import gc
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.ipc_collect()
    except: pass
    gc.collect()
    print("🧹 [System] 显存已清空，准备交接。")

async def get_adaptive_ocr_worker():
    return AdaptiveOCRWorker()
