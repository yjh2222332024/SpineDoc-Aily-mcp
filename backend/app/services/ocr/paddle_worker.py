"""
SpineDoc 确定性感知巡逻兵 (V1.0 - PaddleOCR Edition)
==================================================
架构使命：
1. 绝对确定性：使用判别式 OCR (RapidOCR)，拒绝幻觉。
2. 低显存：锁定在 <1GB，让出资源给核心数据库与 RAG 逻辑。
3. 坐标驱动：为后续的公式缝合提供精确的逻辑锚点。
"""

import numpy as np
import cv2
import time
from typing import List, Dict, Any, Tuple
from rapidocr_onnxruntime import RapidOCR

class PaddleWorker:
    def __init__(self):
        self._engine = None
        self._use_gpu = None

    @property
    def engine(self):
        if self._engine is None:
            import torch
            self._use_gpu = torch.cuda.is_available()
            self._engine = RapidOCR(
                det_use_cuda=self._use_gpu,
                cls_use_cuda=self._use_gpu,
                rec_use_cuda=self._use_gpu
            )
            mode_tag = "CUDA" if self._use_gpu else "CPU"
            print(f" [OCR-Paddle] 确定性感知工兵已就绪 (RapidOCR-ONNX | Device: {mode_tag})")
        return self._engine

    async def ocr_with_layout(self, image_np: np.ndarray) -> List[Dict[str, Any]]:
        """
        提取带坐标的文字块 (The Scout's Duty)
        """
        #  专业的代码不应该在主线程阻塞
        start_time = time.time()
        
        # 确保图像格式正确
        if len(image_np.shape) == 2:
            img_3ch = cv2.cvtColor(image_np, cv2.COLOR_GRAY2BGR)
        else:
            img_3ch = image_np

        # 执行识别
        results, _ = self.engine(img_3ch)
        
        blocks = []
        if results:
            for res in results:
                bbox, text, conf = res
                #  通过置信度和正则，嗅探潜在的公式块
                is_potential_formula = self._is_math_heavy(text, float(conf))
                
                blocks.append({
                    "bbox": bbox, # [top_left, top_right, bottom_right, bottom_left]
                    "text": text,
                    "confidence": float(conf),
                    "type": "formula" if is_potential_formula else "text"
                })
        
        elapsed = time.time() - start_time
        print(f" [OCR-Paddle] 页面嗅探完成，捕获 {len(blocks)} 个区块，耗时 {elapsed:.2f}s")
        return blocks

    def _is_math_heavy(self, text: str, conf: float) -> bool:
        """
        嗅探逻辑：如果置信度极低且包含特殊字符，或者包含明显的数学符号
        """
        math_symbols = ['\\', '{', '}', '^', '_', '=', '+', '-', '*', '/', '(', ')', '[', ']', '<', '>', '|']
        symbol_count = sum(1 for char in text if char in math_symbols)
        
        #  启发式算法：高符号密度或极低置信度的文本块通常是公式
        return symbol_count > 3 or (conf < 0.6 and symbol_count > 0)
