import json
from typing import List, Dict, Any
from openai import AsyncOpenAI
from app.core.config import settings

class StructureAgent:
    """
    StructureAgent V34.0: 幻影脊梁重建大师
    职责：从视觉显著性候选行中，推断出文档的虚拟逻辑树。
    """
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)

    async def synthesize_toc(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        基于物理特征候选行，合成虚拟目录
        """
        # 1. 数据压缩：只发送关键元数据，节省 Token
        compressed_data = []
        for c in candidates:
            compressed_data.append({
                "t": c["text"],
                "s": c["size"],
                "b": c["is_bold"],
                "p": c["page"]
            })

        prompt = f"""你是一个文档结构分析专家。下面是从一份没有目录的 PDF 中通过视觉特征提取的候选行。
你的任务是：
1. 识别真正的【章节标题】，过滤掉作者名、机构名、水印（如 arXiv）以及分散的正文加粗。
2. 推断层级结构（level 1 为最高级，level 2 为子章节...）。
3. 识别典型的编号（如 一、1.1、Chapter 1）。
4. 输出为 JSON 数组格式：[{{"title": "...", "page": 1, "level": 1}}]

候选行数据：
{json.dumps(compressed_data[:100], ensure_ascii=False)} 
"""
        try:
            res = await self.client.chat.completions.create(
                model=settings.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" },
                temperature=0
            )
            data = json.loads(res.choices[0].message.content)
            
            # 🚀 [V34.1] 鲁棒性解析
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict):
                # 尝试各种可能的 key
                for key in ["toc", "chapters", "structure", "items"]:
                    if key in data:
                        items = data[key]
                        break
                else:
                    # 如果没有 key 匹配，但字典本身可能就是目标（虽然不合规但防患未然）
                    items = []
            else:
                items = []
            
            return items
        except Exception as e:
            print(f"⚠️ 虚拟目录合成失败: {e}")
            return []

if __name__ == "__main__":
    # 模拟测试逻辑
    import asyncio
    async def test():
        agent = StructureAgent()
        # 模拟刚才嗅探到的数据
        test_data = [
            {"text": "REAL-MM-RAG: Benchmark", "size": 14.3, "is_bold": True, "page": 1},
            {"text": "Abstract", "size": 12.0, "is_bold": True, "page": 1},
            {"text": "1 Introduction", "size": 12.0, "is_bold": True, "page": 1},
            {"text": "arXiv:2502.12342", "size": 20.0, "is_bold": False, "page": 1},
            {"text": "2 Related Work", "size": 12.0, "is_bold": True, "page": 3},
        ]
        toc = await agent.synthesize_toc(test_data)
        print(json.dumps(toc, indent=2, ensure_ascii=False))
    
    asyncio.run(test())
