import pytest
import asyncio
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 🚀 路径注入
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

# 🔑 强制加载 .env 环境变量
load_dotenv(project_root / ".env")

from backend.app.services.rag.logic_refiner import LogicRefiner

@pytest.mark.asyncio
async def test_refiner_on_dirty_sample():
    """用生产环境捞出的真实脏数据进行测试"""
    sample_path = Path(__file__).parent / "dirty_sample.txt"
    if not sample_path.exists():
        dirty_content = "这是一段脏数据，包含了一些 TOC 逻辑错误，比如标题 1.1 在标题 1 之前。"
    else:
        with open(sample_path, "r", encoding="utf-8") as f:
            dirty_content = f.read()
    
    # 🧠 [V18.0] 逻辑精炼器：将连接至 30001 端口的 SLM 服务
    print(f"📡 Current SLM URL: {os.getenv('SLM_API_URL')}")
    print(f"☁️ Current Embedding Key Loaded: {'Yes' if os.getenv('EMBEDDING_API_KEY') else 'No'}")
    
    refiner = LogicRefiner(api_key=os.getenv("OPENAI_API_KEY"))
    
    print("\n🔍 正在进行脏数据解析测试...")
    # 这里会调用 SLM 服务进行逻辑解构
    result = await refiner._slm_analyze(
        "你是一个【文档结构审计员】。提取5个硬核实体(entities)、逻辑角色(role)和总结(summary)。仅返回标准 JSON。",
        dirty_content[:1000],
        "测试脏章节"
    )
    
    if result is None:
        print("❌ 解析失败，请看控制台打印的原始响应！")
        return False
    else:
        print(f"✅ 解析成功: {result}")
        return True

if __name__ == "__main__":
    asyncio.run(test_refiner_on_dirty_sample())
