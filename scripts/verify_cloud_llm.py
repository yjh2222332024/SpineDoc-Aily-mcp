import asyncio
import os
from backend.app.services.keyword_extractor import get_keyword_extractor

async def verify_llm():
    print("🚀 [Verify] Starting Cloud LLM Keyword Extraction Test...")
    extractor = get_keyword_extractor()
    
    test_text = """
    SpineDoc 是一个云原生知识系统，利用 Bitable 作为单一事实来源。
    它采用了 RAPTOR 递归摘要技术和星系聚类算法，确保逻辑主权。
    """
    
    print(f"📄 Input Text: {test_text.strip()}")
    
    try:
        keywords = await extractor.extract_keywords(test_text, top_n=5)
        if keywords:
            print(f"✅ Success! Extracted Keywords: {', '.join(keywords)}")
        else:
            print("⚠️ Failed: Extractor returned empty list.")
    except Exception as e:
        print(f"❌ Error during verification: {e}")

if __name__ == "__main__":
    # 强制不使用代理进行本地测试，防止 getaddrinfo 错误
    os.environ['NO_PROXY'] = 'volces.com,volcengine.com,feishu.cn'
    asyncio.run(verify_llm())
