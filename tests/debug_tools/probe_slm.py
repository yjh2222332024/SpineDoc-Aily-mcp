import asyncio
import json
from openai import AsyncOpenAI

async def probe():
    # 使用探测到的正确 ID
    client = AsyncOpenAI(api_key="none", base_url="http://127.0.0.1:30001/v1")
    model_id = "/app/models/qwen-1.5b"
    
    print(f"🔍 正在连接模型: {model_id}")
    
    try:
        res = await client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "请返回一个标准的 JSON 格式：{\"entities\": [\"test\"], \"role\": \"test\", \"summary\": \"test\"}"}],
            temperature=0.0,
            timeout=10.0
        )
        content = res.choices[0].message.content
        print(f"✅ 响应内容: {content}")
        # 验证 JSON
        data = json.loads(content)
        print("✅ JSON 解析成功!")
    except Exception as e:
        print(f"❌ 探测失败: {e}")

if __name__ == "__main__":
    asyncio.run(probe())
