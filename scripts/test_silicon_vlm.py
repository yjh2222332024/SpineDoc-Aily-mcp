import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 🚀 路径注入
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

# 🔑 强制加载环境变量
load_dotenv(project_root / ".env", override=True)

from backend.app.services.ocr.ocr_process_utils import render_page_standard, get_adaptive_ocr_worker
from backend.app.core.config import settings

async def test_cloud_vlm_range():
    # 🏛️ 顶级架构师：完全遵循 settings 配置，不再写死模型名
    model_name = settings.VLM_MODEL_NAME
    print(f"📡 [VLM-Test] 启动 9-15 页全量扫描测试...")
    print(f"🤖 Active Model (from settings): {model_name}")
    
    # 1. 准备测试范围 (物理页码 9-15 对应索引 8-14)
    pdf_path = "ceshi_ocr/1.pdf"
    target_indices = list(range(8, 15)) 
    
    # 2. 初始化自适应 Worker
    worker = await get_adaptive_ocr_worker()
    
    if not worker.vlm_worker:
        print("❌ 错误：VLM Worker 未能初始化，请检查 .env 中的 API Key。")
        return

    # 3. 循环处理每一页
    import cv2
    import numpy as np

    for idx in target_indices:
        print(f"\n📸 [Scanning] 正在处理 PDF 物理页面 P{idx+1}...")
        _, img_bytes = render_page_standard(pdf_path, idx, scale=2.0)
        
        if img_bytes is None:
            print(f"❌ P{idx+1} 渲染失败")
            continue

        nparr = np.frombuffer(img_bytes, np.uint8)
        img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 4. 调用高精度 VLM 路径
        result = await worker.ocr_to_markdown(img_np, high_precision=True)
        
        if result:
            print(f"✅ [P{idx+1}] 识别成功！提取内容预览：")
            print("-" * 40)
            # 打印前 200 个字符
            print(result.strip() + "...")
            print("-" * 40)
        else:
            print(f"🚨 [P{idx+1}] VLM ({model_name}) 未返回任何内容。")
        
        # 冷却
        await asyncio.sleep(1.0)

if __name__ == "__main__":
    asyncio.run(test_cloud_vlm_range())
