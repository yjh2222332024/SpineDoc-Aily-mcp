"""
SpineDoc ARK 逻辑熔炼器 (V1.0 豆包重构版)
=======================================
职责：利用豆包 2.0 (ARK) 的高阶推理能力，将 OCR 碎块重构为结构化 TOC。
     这是“逻辑熔断（Logic Smelting）”策略的中枢。
"""
import json
import asyncio
import re
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from backend.app.core.config import settings

class ARKLogicSmelter:
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.ARK_API_KEY,
            base_url=settings.ARK_BASE_URL
        )
        self.endpoint = settings.ARK_ENDPOINT

    async def smelt_toc(self, raw_blocks: List[Dict[str, Any]], page_context: str = "") -> List[Dict[str, Any]]:
        """
        🚀 逻辑熔断：将 OCR 碎块重构为结构化 JSON。
        """
        if not raw_blocks:
            return []

        # 1. 准备物料：将碎块转化为紧凑的描述字符串
        # 格式：[Text] (x,y)
        blocks_desc = []
        for b in raw_blocks:
            text = b.get("text", "").strip()
            if not text: continue
            # 简化坐标，仅提取左上角
            bbox = b.get("bbox", [])
            coord = f"({bbox[0]['x']},{bbox[0]['y']})" if bbox else "(?,?)"
            blocks_desc.append(f"Content: '{text}' @ {coord}")

        materials = "\n".join(blocks_desc)

        # 2. 强约束 Prompt
        prompt = f"""你是一个顶级的法律文档结构审计员。
下面是从 OCR 引擎中提取的原始文本块及其物理坐标位置。
由于识别或排版原因，这些块的顺序可能错乱，文字可能存在轻微识别错误。

【任务】
1. 根据文本的语义内容、物理坐标（y 轴判定先后，x 轴判定缩进）以及文档逻辑常理，重构出完整的目录结构。
2. 识别出每个条目的层级（1/2/3级标题）。
3. 修正明显的 OCR 识别错误（例如 '第1节' 识别为 '第I节'）。
4. 提取出每个条目对应的【逻辑页码】。

【上下文信息】
{page_context}

【原始文本碎块】
{materials}

✅ 输出规范：
1. 仅返回一个标准 JSON 数组。
2. 数组中的每个对象包含：'title'(字符串), 'logical_page'(整数), 'level'(整数)。
3. 严禁任何解释、说明或 Markdown 代码块包裹。
"""

        try:
            # 3. 调用豆包 2.0 执行逻辑重构
            response = await self.client.chat.completions.create(
                model=self.endpoint,
                messages=[
                    {"role": "system", "content": "你是一个只输出标准 JSON 数组的专业文档结构解析器。严禁输出任何 Markdown 标记或解释。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )

            raw_content = response.choices[0].message.content.strip()
            
            # 4. 🚀 [V54.5] 多重 JSON 过滤层
            # 4.1 移除可能存在的 Markdown 块
            clean_content = re.sub(r'```json\s*|\s*```', '', raw_content)
            # 4.2 正则物理打捞
            json_match = re.search(r'\[\s*{.*}\s*\]', clean_content, re.DOTALL)
            
            if json_match:
                candidate_text = json_match.group(0)
                try:
                    data = json.loads(candidate_text)
                    # 4.3 语义校验与 Schema 对齐
                    refined_items = []
                    for it in data:
                        if isinstance(it, dict) and "title" in it:
                            # 强制类型对齐
                            item = {
                                "title": str(it.get("title", "")).strip(),
                                "logical_page": self._safe_int(it.get("logical_page") or it.get("page", 0)),
                                "level": self._safe_int(it.get("level", 1))
                            }
                            if item["title"]:
                                refined_items.append(item)
                    
                    print(f"✅ [Smelter] 逻辑重构完成: 原始 {len(data)} 项 -> 校验后 {len(refined_items)} 项")
                    return refined_items
                except json.JSONDecodeError as je:
                    print(f"❌ [Smelter] JSON 解析失败: {je} | 原始内容: {candidate_text[:100]}")
            
            return []

        except Exception as e:
            print(f"❌ [Smelter] 核心异常: {e}")
            return []

    def _safe_int(self, val, default=0) -> int:
        if isinstance(val, int): return val
        if not val: return default
        try:
            return int(str(val).strip())
        except:
            nums = re.findall(r'\d+', str(val))
            return int(nums[0]) if nums else default

ark_smelter = ARKLogicSmelter()
