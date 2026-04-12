import asyncio
import os
import numpy as np
import cv2
from dotenv import load_dotenv
from backend.app.services.ocr.zhipu_worker import ZhipuCloudWorker

async def verify_zhipu_算力():
    # 1. 加载环境变量
    load_dotenv()
    api_key = os.getenv("ZHIPU_API_KEY")
    
    if not api_key:
        print("❌ [Verification] 未在 .env 中发现 ZHIPU_API_KEY。")
        return

    print(f"📡 [Verification] 正在连接智谱云端 (Key: {api_key[:6]}...{api_key[-4:]})")
    
    try:
        # 2. 初始化 Worker
        worker = ZhipuCloudWorker(api_key=api_key)
        
        # 3. 创建一个 200x200 的空白虚拟页面进行测试
        dummy_img = np.ones((200, 200, 3), dtype=np.uint8) * 255
        
        print("⏳ [Verification] 正在发起布局解析请求...")
        result = await worker.ocr_to_markdown(dummy_img)
        
        if result:
            print(f"✅ [Verification] 拨测成功！智谱响应内容: {result[:100]}...")
            print("\n🌟 结论：您的智谱 API Key 有效，云端感知层已就绪。")
        else:
            print("⚠️ [Verification] 响应为空，但通道已接通。")
            
    except Exception as e:
        print(f"❌ [Verification] 拨测失败！错误详情: {e}")
        if "401" in str(e) or "Unauthorized" in str(e):
            print("👉 提示：API Key 似乎无效或已过期。")
        elif "No module named 'zai'" in str(e):
            print("👉 提示：请先运行 'pip install zai-sdk==0.2.2' 安装智谱 SDK。")

if __name__ == "__main__":
    asyncio.run(verify_zhipu_算力())
