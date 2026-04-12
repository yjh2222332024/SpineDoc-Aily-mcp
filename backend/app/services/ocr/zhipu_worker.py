"""
SpineDoc ZhipuCloudWorker - V1.0 (Official SDK Edition)
======================================================
职责：调用智谱 GLM-OCR (0.9B) 云端 API 进行高精度布局解析。
"""
import os
import io
import asyncio
import numpy as np
from PIL import Image
from typing import List, Dict, Any, Optional
from zai import ZhipuAiClient

class ZhipuCloudWorker:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ZHIPU_API_KEY")
        if not self.api_key:
            raise ValueError("❌ [ZhipuWorker] 未检测到 ZHIPU_API_KEY，请检查环境变量。")
        
        self.client = ZhipuAiClient(api_key=self.api_key)
        print(f"🔗 [Zhipu-Worker] 云端算力已接通 (Model: glm-ocr)")

    async def ocr_to_markdown(self, image_np: np.ndarray) -> str:
        """
        将 OpenCV/Numpy 图像转化为 Markdown。
        由于 zai-sdk 目前是同步阻塞调用，我们将其包装在 thread pool 中以防阻塞事件循环。
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_ocr, image_np)

    def _sync_ocr(self, image_np: np.ndarray) -> str:
        import base64
        try:
            # 1. 将图像转换为高质量 JPEG 字节流
            pil_img = Image.fromarray(image_np)
            img_byte_arr = io.BytesIO()
            pil_img.save(img_byte_arr, format='JPEG', quality=90)
            img_bytes = img_byte_arr.getvalue()
            
            # 2. 🚀 [V1.2.6 Fix] 编码为 Base64 Data URI
            # 这样既能避开 JSON 序列化错误，也能解决云端无法访问本地文件的问题
            base64_data = base64.b64encode(img_bytes).decode("utf-8")
            data_uri = f"data:image/jpeg;base64,{base64_data}"
            
            # 3. 调用布局解析 (传递字符串而非流)
            response = self.client.layout_parsing.create(
                model="glm-ocr",
                file=data_uri
            )
            
            # 4. 深度提取结果 (zai-sdk 返回的是对象)
            # 尝试多种可能的字段名以增强兼容性
            for attr in ['content', 'data', 'result', 'text']:
                if hasattr(response, attr):
                    val = getattr(response, attr)
                    if val: return str(val)
            
            # 兜底：尝试从字典形式提取 (有些 SDK 版本支持 .dict())
            try:
                res_dict = response.model_dump() if hasattr(response, 'model_dump') else response.__dict__
                return str(res_dict.get('content') or res_dict.get('data') or response)
            except:
                return str(response)
            
        except Exception as e:
            print(f"🚨 [Zhipu-Cloud] 失败: {e}")
            return ""

    async def ocr_page_batch(self, image_nps: List[np.ndarray], indices: List[int]) -> Dict[int, str]:
        """并发执行批量 OCR"""
        tasks = [self.ocr_to_markdown(img) for img in image_nps]
        results = await asyncio.gather(*tasks)
        return {idx: res for idx, res in zip(indices, results)}
