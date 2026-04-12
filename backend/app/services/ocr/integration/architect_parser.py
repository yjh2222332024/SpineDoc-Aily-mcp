import asyncio
# 🔥 修复 Python 路径问题（Windows 专用）
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent  # 跳到项目根目录
sys.path.append(str(project_root))
import os
import re
import uuid
import time
import fitz
import base64
import numpy as np
from typing import List, Dict, Any, Optional
from backend.app.services.toc.base import SpineNode
from concurrent.futures import ProcessPoolExecutor
from ..ocr_process_utils import render_page_standard, get_adaptive_ocr_worker

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
    SpineDoc 架构师级视觉目录解析器 (V33.0 归一化版)
    职责：仅负责目录的视觉识别与逻辑重构。算力由统一中心调度。
    """
    def __init__(self, mode="auto", **kwargs):
        print("🚀 [System] ArchitectVisualParser V33.0 (Hardened) 启动...")
        self.worker = None # 懒加载
        self.queue = asyncio.Queue(maxsize=32)
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
                    # 🚀 [V1.4.0] 关键分流：目录页启用 high_precision
                    md_content = await worker.ocr_to_markdown(img_np, high_precision=high_precision)
                    raw_texts[page_idx] = md_content
                    print(f"📄 [TOC-Sense] 页面 P{page_idx+1} 识别完成 ({'VLM' if high_precision else 'GLM'})")
                    
                    # 🚀 [V1.2.8] 云端强制冷却，防止 429
                    if high_precision:
                        await asyncio.sleep(1.0)
                        
                except Exception as e:
                    print(f"⚠️ Page {page_idx+1} OCR 异常: {e}")
            self.queue.task_done()

    async def _structure_toc_with_agent(self, page_texts: Dict[int, str], allowed_pages: Optional[List[int]]) -> List[Dict[str, Any]]:
        from openai import AsyncOpenAI
        from app.core.config import settings
        import json

        client = AsyncOpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        model_name = settings.LLM_MODEL_NAME

        async def process_single_page(p_idx, text):
            if allowed_pages is not None:
                if (p_idx + 1) not in allowed_pages: return []
            if not text or not text.strip(): return []
            
            prompt = """你是一个全能的【文档逻辑架构师】。你的任务是从 OCR 文本中提取文档的【逻辑骨架/目录】。
            
            ✅ 泛化规则：
            1. **多语种支持**：准确识别中文（章/节/项）、英文（Chapter/Section）、甚至无编号但加粗的标题。
            2. **视觉层级判定**：字号较大、独立成行、位于页面中心或左侧的内容通常是潜在标题。
            3. **逻辑一致性**：提取后的标题应能构成文档的导航索引。
            
            ⚠️ 严禁提取：
            - 正文叙述段落。
            - 脚注、页码注释、作者介绍。
            - 图表内部的标注文字。
            
            输出格式：JSON 数组，如 [{"title": "标题内容", "page": 逻辑页码, "level": 1(主标题)/2(副标题)}]
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
                if isinstance(data, dict): data = [data]
                
                valid_items = []
                for it in data:
                    if isinstance(it, dict) and "title" in it:
                        it["page"] = safe_int(it.get("page", 0))
                        it["level"] = safe_int(it.get("level", 1))
                        # 🚀 [Fix] physical_page = page (都是指正文所在的物理页码)
                        it["physical_page"] = p_idx + 1 
                        valid_items.append(it)
                return valid_items
            except Exception as e:
                print(f"⚠️ P{p_idx+1} 语义解析失败: {e}")
                return []

        tasks = [process_single_page(i, page_texts[i]) for i in sorted(page_texts.keys())]
        print(f"🧠 [Agent] 正在重构主权逻辑地图...")
        results = await asyncio.gather(*tasks)
        
        from backend.app.services.toc.base import SpineNode
        import uuid

        all_toc_items = []
        for r in results:
            for it in r:
                n = SpineNode(
                    id=uuid.uuid4(),
                    title=it.get("title", "").strip(),
                    level=safe_int(it.get("level", 1)),
                    logical_page=safe_int(it.get("page", 1)),
                    source="ocr_agent"
                )
                all_toc_items.append(n)
        
        if not all_toc_items:
            return [SpineNode(title="Main Content", logical_page=1, level=1)]
            
        final_toc = []
        seen_titles = set()
        for i, n in enumerate(all_toc_items):
            if not n.title or n.title in seen_titles: continue
            n.index = i
            final_toc.append(n)
            seen_titles.add(n.title)
        return final_toc

    async def rebuild_spine_concurrently(self, file_path: str,
                                         max_sniff_pages: int = 0,
                                         manual_range: Optional[List[int]] = None) -> List[SpineNode]:
        """
        🚀 全文 OCR + LLM 语义分析提取 TOC
        
        Args:
            max_sniff_pages: 扫描页数 (0=扫描全文，>0=扫描指定页数)
            manual_range: 用户手动指定的页码范围
        """
        start_time = time.time()
        try:
            # 🚀 [V33.1] 智能探测：先找目录位置
            if manual_range is None:
                # 用户没有指定范围 → 智能探测目录位置
                toc_location = await self._find_toc_location(file_path)
                if toc_location:
                    print(f"🔍 [SmartScan] 探测到目录在 P{toc_location+1}")
                    # 从目录页开始，扫描后 45 页
                    target_indices = list(range(toc_location, min(len(fitz.open(file_path)), toc_location + max_sniff_pages)))
                else:
                    # 未找到目录 → 扫描全文 (max_sniff_pages=0) 或前 45 页
                    total_pages = len(fitz.open(file_path))
                    if max_sniff_pages == 0:
                        target_indices = list(range(total_pages))  # 🚀 扫描全文
                        print(f"🔍 [SmartScan] 未找到目录位置，扫描全文 {total_pages} 页")
                    else:
                        target_indices = list(range(min(total_pages, max_sniff_pages)))
                        print(f"🔍 [SmartScan] 未找到目录位置，扫描前 {max_sniff_pages} 页")
            else:
                # 用户指定了范围
                target_indices = sorted([p - 1 for p in manual_range])

            toc_offset = int(max(manual_range)) if manual_range else 0
            print(f"⚖️ [Commander] 锁定物理偏移 Offset = {toc_offset}")

            raw_page_texts = {}
            # 🚀 [V1.2.8] 极致限速：云端仅开启单线模式
            worker = await self._ensure_worker()
            num_workers = 1 if worker and "Zhipu" in str(type(worker)) else 16

            workers = [asyncio.create_task(self._ocr_consumer(raw_page_texts)) for _ in range(num_workers)]

            loop = asyncio.get_running_loop()
            max_render_workers = min(os.cpu_count() // 2, 4)
            with ProcessPoolExecutor(max_workers=max_render_workers) as executor:
                render_tasks = [loop.run_in_executor(executor, render_page_standard, file_path, i, 1.2) for i in target_indices]
                for coro in asyncio.as_completed(render_tasks):
                    p_idx, img_bytes = await coro
                    await self.queue.put((p_idx, img_bytes))

            for _ in range(num_workers): await self.queue.put(None)
            await asyncio.gather(*workers)
            await self.queue.join()

            final_toc = await self._structure_toc_with_agent(raw_page_texts, allowed_pages=manual_range)
            for item in final_toc:
                item.logical_page = item.logical_page + toc_offset

            print(f"✅ [V33.0-Done] 逻辑脊梁重构完成 | 耗时: {time.time()-start_time:.2f}s")
            return final_toc
        except Exception as e:
            print(f"🚨 [V33.0-Critical] 流程崩溃：{e}")
            return [SpineNode(title="Full Document", logical_page=1, level=1)]

    def extract_toc_async(self, file_path: str, manual_range: Optional[List[int]] = None):
        return self.rebuild_spine_concurrently(file_path, manual_range=manual_range)
