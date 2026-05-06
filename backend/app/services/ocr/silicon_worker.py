"""
SpineDoc SiliconFlow VLM 工作器 - 2026/04/11 极简 JSON 版
=====================================================
职责：将文档图片精准转化为结构化 JSON 数组，严禁任何废话。
"""
import os
import base64
import cv2
import json
import re
import numpy as np
from openai import AsyncOpenAI
from typing import Optional, List, Dict

class SiliconVLMWorker:
    def __init__(self, api_key: str, base_url: str, model_name: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name

    async def ocr_to_markdown(self, img_np: np.ndarray, high_precision: bool = False) -> Optional[str]:
        """
         核心：图像转 JSON。虽然函数名带 markdown，但为了契约对齐，我们输出 JSON 字符串。
        """
        try:
            # 1. 编码图片
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
            _, buffer = cv2.imencode('.jpg', img_np, encode_param)
            base64_image = base64.b64encode(buffer).decode('utf-8')

            # 2. 强约束 Prompt
            prompt = """你是一个高精度的【文档结构提取器】。
请识别图中所有的章节标题和对应的逻辑页码。

 输出规范：
1. 仅返回一个 JSON 数组。
2. 每个对象包含：'title'(字符串), 'logical_page'(整数), 'level'(1/2/3)。
3. 严禁任何 Markdown 标记、Markdown 块（```json）或多余的文字说明。

示例：
[{"title": "第一章", "logical_page": 1, "level": 1}]"""

            # 3. 调用 API
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}", "detail": "high"}
                            }
                        ]
                    }
                ],
                temperature=0.0
            )
            
            raw_content = response.choices[0].message.content.strip()
            
            # 4. 机械打捞 JSON (防止模型不听话加了 ```json)
            json_match = re.search(r'\[.*\]', raw_content.replace('\n', ''), re.DOTALL)
            if json_match:
                return json_match.group(0)
            return raw_content # 兜底返回
            
        except Exception as e:
            print(f" [SiliconVLM] 结构化 OCR 失败: {e}")
            return None
