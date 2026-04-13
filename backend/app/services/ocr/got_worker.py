"""
SpineDoc GOT-OCR 2.0 精修专家 (V1.0)
==================================
架构使命：
1. 极致抗噪：能够完美处理带文字的公式切片。
2. 580M 全能王：原生支持 Markdown 与 LaTeX 输出。
3. 显存友好：FP16 模式下仅占 ~1.5GB 显存。
"""

import torch
import os
from transformers import AutoModelForImageTextToText, AutoProcessor
from PIL import Image
import numpy as np
import cv2
from typing import Optional
from pathlib import Path
from backend.app.core.config import settings

class GOTWorker:
    def __init__(self, model_id: str = "stepfun-ai/GOT-OCR-2.0-hf"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
        
        # 🏛️ 持久化存储：使用全局配置中的 CACHE_DIR
        base_cache = Path(settings.CACHE_DIR)
        cache_dir = str(base_cache / "GOT-OCR-2.0")
        os.makedirs(cache_dir, exist_ok=True)
        
        print(f"🚀 [OCR-GOT] 正在加载模型 {model_id} (Cache: {cache_dir}) 到 {self.device}...")
        
        try:
            self.model = AutoModelForImageTextToText.from_pretrained(
                model_id,
                torch_dtype=self.dtype,
                low_cpu_mem_usage=True,
                trust_remote_code=True,
                cache_dir=cache_dir
            ).to(self.device)
            
            self.processor = AutoProcessor.from_pretrained(
                model_id, 
                trust_remote_code=True,
                cache_dir=cache_dir
            )
            print(f"✅ [OCR-GOT] 模型加载完成 (Device: {self.device})")
        except Exception as e:
            print(f"❌ [OCR-GOT] 模型加载失败: {e}")
            raise e

    def refine_content(self, crop_np: np.ndarray) -> str:
        """
        全能精修：处理公式及其周围可能的文字噪声
        """
        if crop_np is None or crop_np.size == 0:
            return ""
        
        try:
            # 🏛️ 转换为 PIL Image
            image = Image.fromarray(cv2.cvtColor(crop_np, cv2.COLOR_BGR2RGB))
            
            # 🏛️ 关键配置：format=True 开启公式/表格的 Markdown 渲染
            inputs = self.processor(image, return_tensors="pt", format=True).to(self.device, self.dtype)
            
            # 执行推理
            with torch.no_grad():
                generate_ids = self.model.generate(
                    **inputs,
                    do_sample=False,
                    tokenizer=self.processor.tokenizer,
                    stop_strings="<|im_end|>",
                    max_new_tokens=1024,
                )
            
            # 解码
            content = self.processor.decode(generate_ids[0], skip_special_tokens=True).strip()
            
            # 🏛️ 专业的后处理：移除 Chat Template 泄露产生的冗余标签
            # GOT-OCR-2.0-hf 有时会输出 system/user/assistant 的对话结构
            if "assistant" in content:
                content = content.split("assistant")[-1].strip()
            
            # 简单清理可能残留的引导性文本
            content = content.replace("OCR with format:", "").strip()
            
            return content
        except Exception as e:
            print(f"⚠️ [OCR-GOT] 精修失败: {e}")
            return ""
