"""
SpineDoc GOT-OCR 2.0 集成测试 (The Deterministic Lab V2)
======================================================
架构使命：
1. 验证 PaddleOCR (Scout) + GOT-OCR 2.0 (Specialist) 的协同工作。
2. 验证并发识别与索引驱动的重排序逻辑。
3. 观察 GOT 对带噪声公式切片的抗噪表现。
"""

import asyncio
import numpy as np
import cv2
import os
import sys
import time
from pathlib import Path

# 🏛️ 确保导入路径覆盖项目根目录
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from backend.app.services.ocr.ocr_process_utils import get_adaptive_ocr_worker

async def run_got_integration_test():
    """
    执行 GOT 驱动的集成审计流程
    """
    test_image_path = Path("ceshi_ocr/image.png")
    if not test_image_path.exists():
        print(f"❌ [Lab] 未找到测试图片: {test_image_path}")
        return

    print(f"🚀 [Lab] 正在启动 GOT-OCR 2.0 集成测试，读取样本: {test_image_path}...")
    
    # 1. 初始化集成 Worker
    start_init = time.time()
    worker = await get_adaptive_ocr_worker()
    print(f"✅ [Lab] Worker 初始化完成，耗时 {time.time() - start_init:.2f}s")
    
    # 2. 读取图像
    img = cv2.imread(str(test_image_path))
    if img is None:
        print("❌ [Lab] 无法读取图像")
        return

    # 3. 执行端到端识别
    print("👁️ [Lab] 正在执行端到端确定性识别 (Paddle + GOT 并发)...")
    start_ocr = time.time()
    
    # 我们直接调用主入口，验证其内部的并发与排序逻辑
    markdown_result = await worker.ocr_to_markdown(img)
    
    elapsed = time.time() - start_ocr
    print(f"⚡ [Lab] 识别任务结束，总耗时 {elapsed:.2f}s")

    # 4. 结果展示与断言
    print("\n" + "="*40)
    print("🏛️ [Lab] GOT-OCR 2.0 解析报告：")
    print(markdown_result[:2000] + ("..." if len(markdown_result) > 2000 else ""))
    print("="*40)

    # 🏛️ 核心检查点
    # 1. 检查是否捕获了 LaTeX 公式符号 (通常包含 \ 或者 $)
    has_math = "\\" in markdown_result or "$" in markdown_result
    # 2. 检查是否还有英文提示词幻觉
    bad_words = ["Looking", "closely", "here is", "for example", "maybe"]
    hallucinations = [w for word in bad_words if word.lower() in markdown_result.lower()]

    if has_math and not hallucinations:
        print(f"\n✨ [Lab] 测试大获全胜！成功提取公式且零幻觉污染。")
    elif hallucinations:
        print(f"\n⚠️ [Lab] 警告：发现疑似幻觉词汇 {hallucinations}")
    else:
        print("\n🤔 [Lab] 未检测到公式，请检查 PaddleOCR 嗅探逻辑。")

if __name__ == "__main__":
    # 🏛️ Windows 异步支持
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_got_integration_test())
