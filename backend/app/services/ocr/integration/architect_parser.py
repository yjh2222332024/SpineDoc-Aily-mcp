import asyncio
# 🔥 修复 Python 路径问题（Windows 专用）
import sys
from pathlib import Path
# 🏛️ 顶级架构师：必须精准回退 5 级才能到达项目根目录 (E:\study\code\spine-close\Spine-close)
project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import os
import re
import uuid
import time
import fitz
import base64
import numpy as np
from typing import List, Dict, Any, Optional
from backend.app.services.toc.base import SpineNode
from backend.app.services.ocr.ocr_process_utils import render_page_standard, get_adaptive_ocr_worker

def safe_int(val, default=0):
    if isinstance(val, int): return val
    if not val: return default
    s = str(val).strip()
    try:
        return int(s)
    except:
        nums = re.findall(r'\d+', s)
        return int(nums[-1]) if nums else default

class ArchitectVisualParser:
    """
    SpineDoc 架构师级视觉目录解析器 (V34.7 资源敏感版)
    职责：
    1. 针对 Windows 环境，采用单句柄顺序渲染。
    2. 严格遵循全局单例 Worker，消灭幽灵实例。
    """
    def __init__(self, mode="auto", **kwargs):
        print("🚀 [System] ArchitectVisualParser V34.7 (Ready) 启动...")
        self.worker = None 
        self.queue = asyncio.Queue(maxsize=64)
        self.semaphore = asyncio.Semaphore(16)

    async def _ensure_worker(self):
        if self.worker is None:
            self.worker = await get_adaptive_ocr_worker()
        return self.worker

    async def _ocr_consumer(self, raw_texts: Dict[int, str], high_precision: bool = False):
        worker = await self._ensure_worker()
        while True:
            item = await self.queue.get()
            if item is None:
                self.queue.task_done()
                break
            
            page_idx, img_bytes = item
            if img_bytes is None or worker is None:
                self.queue.task_done()
                continue

            async with self.semaphore:
                try:
                    nparr = np.frombuffer(img_bytes, np.uint8)
                    import cv2
                    img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    md_content = await worker.ocr_to_markdown(img_np, high_precision=high_precision)
                    raw_texts[page_idx] = md_content
                    mode_tag = "VLM" if high_precision else "GLM"
                    print(f"📄 [TOC-Sense] 页面 P{page_idx+1} 识别完成 ({mode_tag})")
                    
                    if high_precision:
                        await asyncio.sleep(1.0) # 冷却
                        
                except Exception as e:
                    print(f"⚠️ Page {page_idx+1} OCR 异常: {e}")
            self.queue.task_done()

    async def _structure_toc_with_agent(self, page_texts: Dict[int, str], allowed_pages: Optional[List[int]]) -> List[Dict[str, Any]]:
        from openai import AsyncOpenAI
        from backend.app.core.config import settings
        import json

        client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        model_name = settings.LLM_MODEL_NAME

        async def process_single_page(p_idx, text):
            if allowed_pages is not None:
                if (p_idx + 1) not in allowed_pages: return []
            if not text or not text.strip(): return []
            
            if text.strip().startswith("[") and text.strip().endswith("]"):
                try:
                    data = json.loads(text)
                    valid_items = []
                    for it in data:
                        if isinstance(it, dict) and "title" in it:
                            it["logical_page"] = safe_int(it.get("logical_page") or it.get("page", 0))
                            it["level"] = safe_int(it.get("level", 1))
                            valid_items.append(it)
                    return valid_items
                except: pass

            prompt = """你是一个全能的【文档逻辑架构师】。提取目录中的章节标题及其对应的页码。
            输出格式：JSON 数组，如 [{"title": "标题", "logical_page": 1, "level": 1}]
            OCR 文本：\n%s""" % text

            try:
                response = await client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.0
                )
                content = response.choices[0].message.content
                json_match = re.search(r'\[.*\]', content.replace("```json","").replace("```",""), re.DOTALL)
                if not json_match: return []
                data = json.loads(json_match.group(0))
                valid_items = []
                for it in (data if isinstance(data, list) else [data]):
                    if isinstance(it, dict) and "title" in it:
                        it["logical_page"] = safe_int(it.get("logical_page") or it.get("page", 0))
                        it["level"] = safe_int(it.get("level", 1))
                        valid_items.append(it)
                return valid_items
            except Exception as e:
                print(f"⚠️ P{p_idx+1} 语义解析失败: {e}")
                return []

        tasks = [process_single_page(i, page_texts[i]) for i in sorted(page_texts.keys())]
        print(f"🧠 [Agent] 正在重构主权逻辑地图...")
        results = await asyncio.gather(*tasks)
        
        all_toc_items = []
        for r in results:
            for it in r:
                n = SpineNode(
                    id=uuid.uuid4(),
                    title=it.get("title", "").strip(),
                    level=safe_int(it.get("level", 1)),
                    logical_page=safe_int(it.get("logical_page", 1)),
                    source="ocr_vlm"
                )
                all_toc_items.append(n)
        
        return all_toc_items

    async def rebuild_spine_concurrently(self, file_path: str,
                                         max_sniff_pages: int = 0,
                                         manual_range: Optional[List[int]] = None,
                                         is_toc_task: bool = False) -> List[SpineNode]:
        """
        🚀 [V34.7] 资源敏感型流式识别入口
        """
        start_time = time.time()
        try:
            if manual_range:
                target_indices = sorted([p - 1 for p in manual_range])
            else:
                with fitz.open(file_path) as doc:
                    total = len(doc)
                target_indices = list(range(min(total, max_sniff_pages or 5)))

            raw_page_texts = {}
            num_workers = 1 if is_toc_task else 4 

            workers = [asyncio.create_task(self._ocr_consumer(raw_page_texts, high_precision=is_toc_task)) for _ in range(num_workers)]

            try:
                with fitz.open(file_path) as doc:
                    for i in target_indices:
                        if i >= len(doc): continue
                        page = doc[i]
                        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                        img_bytes = pix.tobytes("jpg")
                        del pix
                        await self.queue.put((i, img_bytes))
                        import gc
                        gc.collect()
            except Exception as e:
                print(f"❌ [Render] 流式渲染中断: {e}")

            for _ in range(num_workers): await self.queue.put(None)
            await asyncio.gather(*workers)

            final_toc = await self._structure_toc_with_agent(raw_page_texts, allowed_pages=manual_range)
            return final_toc
        except Exception as e:
            print(f"🚨 [Critical] 系统级崩溃：{e}")
            return [SpineNode(title="Full Document", logical_page=1, level=1)]

    async def harvest_text_async(self, file_path: str, page_range: List[int]) -> str:
        """
        🚀 [V1.5.0] 纯净收割：仅提取文本流，为语义分片提供原材料。
        """
        start_time = time.time()
        target_indices = sorted([p - 1 for p in page_range])
        raw_page_texts = {}
        
        num_workers = 4 
        workers = [asyncio.create_task(self._ocr_consumer(raw_page_texts, high_precision=False)) for _ in range(num_workers)]

        try:
            with fitz.open(file_path) as doc:
                for i in target_indices:
                    if i >= len(doc): continue
                    page = doc[i]
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.2, 1.2))
                    img_bytes = pix.tobytes("jpg")
                    del pix
                    await self.queue.put((i, img_bytes))
                    import gc
                    gc.collect()
        except Exception as e:
            print(f"❌ [Harvest] 渲染异常: {e}")

        for _ in range(num_workers): await self.queue.put(None)
        await asyncio.gather(*workers)

        full_text = ""
        for i in target_indices:
            if i in raw_page_texts:
                page_text = raw_page_texts[i] or ""
                if re.search(r'(\d+\.){5,}', page_text):
                    print(f"⚠️ [Sanitizer] 检测到 P{i+1} 产生复读幻觉，执行拦截清洗。")
                    page_text = re.sub(r'(\d+\.){5,}.*', ' [检测到 OCR 幻觉，已自动清理] ', page_text)
                full_text += f"\n【物理页码：P{i+1}】\n" + page_text
        
        print(f"✅ [Harvest-Done] 范围 P{min(page_range)}-P{max(page_range)} 收割完成 | 耗时: {time.time()-start_time:.2f}s")
        return full_text

    def extract_toc_async(self, file_path: str, manual_range: Optional[List[int]] = None):
        return self.rebuild_spine_concurrently(file_path, manual_range=manual_range, is_toc_task=True)
