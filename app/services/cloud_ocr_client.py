"""
云端OCR客户端 - V12.0 SiliconFlow 驱动版
职责：利用 Qwen2-VL-72B 提取高精度目录，彻底解决逻辑漂移。
"""
import base64
import io
import asyncio
import aiohttp
import numpy as np
from typing import List, Dict, Any, Optional
from enum import Enum
from PIL import Image
from app.core.config import settings

class OCRProvider(Enum):
    QWEN = "qwen"
    ALIBABA = "alibaba"
    OFFLINE = "offline"

class OCRResult:
    def __init__(self, text: str, confidence: float, bbox: List[List[float]], 
                 provider: str, page_idx: Optional[int] = None):
        self.text = text; self.confidence = confidence; self.bbox = bbox 
        self.provider = provider; self.page_idx = page_idx
    def to_dict(self):
        return {"text": self.text, "confidence": self.confidence, "bbox": self.bbox, 
                "provider": self.provider, "page_idx": self.page_idx}

class CloudOCRService:
    def __init__(self):
        # 🆕 使用 SiliconFlow 作为主驱动
        self.api_key = settings.LLM_API_KEY 
        self.base_url = "https://api.siliconflow.cn/v1"
        self.is_enabled = bool(self.api_key and len(self.api_key) > 10)
        self.session = None

    async def ocr_single_page(self, image: np.ndarray, page_idx: int, provider=None) -> List[OCRResult]:
        if not self.is_enabled:
            print(f"🚫 [OFFLINE] SiliconFlow Key 未就绪，Page {page_idx+1} 强制本地。")
            return []
        
        # 将图片转为 Base64
        pil_img = Image.fromarray(image)
        buf = io.BytesIO(); pil_img.save(buf, format='PNG'); buf.seek(0)
        b64_img = base64.b64encode(buf.getvalue()).decode('utf-8')

        payload = {
            "model": "Qwen/Qwen2-VL-72B-Instruct",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": "OCR this image. Extract every line of the table of contents. Maintain the relationship between title and page number."},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
                ]
            }],
            "max_tokens": 2048, "temperature": 0.1
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        try:
            if not self.session: self.session = aiohttp.ClientSession()
            async with self.session.post(f"{self.base_url}/chat/completions", json=payload, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"]
                    # Qwen2-VL 吐出的是纯文本，我们按行分割
                    lines = content.split('\n')
                    print(f"✅ [SiliconFlow] Page {page_idx+1} 提取成功")
                    return [OCRResult(l.strip(), 0.99, [[0,0],[0,0],[0,0],[0,0]], "qwen", page_idx) for l in lines if len(l.strip()) > 1]
                elif resp.status == 429:
                    print(f"🚦 [Rate-Limit] SiliconFlow 429")
                return []
        except Exception as e:
            print(f"🚨 [Cloud-Error] {e}")
            return []

cloud_ocr_service = CloudOCRService()
