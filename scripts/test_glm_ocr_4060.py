
import asyncio
import httpx
import base64
import time
import os
import fitz  # PyMuPDF
from typing import List, Dict, Any
from concurrent.futures import ProcessPoolExecutor

# 🚀 渲染函数抽离，用于多进程调用
def render_pdf_page(pdf_path, page_idx):
    doc = fitz.open(pdf_path)
    page = doc[page_idx]
    # 🚀 极致性能调优：0.8x 缩放
    pix = page.get_pixmap(matrix=fitz.Matrix(0.8, 0.8))
    img_bytes = pix.tobytes("png")
    doc.close()
    return page_idx, img_bytes

class GLM4060Turbo:
    """4060 最终巅峰版：多核渲染 + 16路并发 OCR"""
    
    def __init__(self, endpoint: str = "http://localhost:30000/v1/chat/completions"):
        self.endpoint = endpoint
        self.client = httpx.AsyncClient(timeout=60.0, limits=httpx.Limits(max_connections=50))
        self.semaphore = asyncio.Semaphore(16)
        self.queue = asyncio.Queue(maxsize=64)

    async def ocr_worker(self, results: List[Dict[str, Any]]):
        while True:
            item = await self.queue.get()
            if item is None:
                self.queue.task_done()
                break
            
            page_idx, img_bytes = item
            async with self.semaphore:
                img_b64 = base64.b64encode(img_bytes).decode('utf-8')
                payload = {
                    "model": "/model",
                    "messages": [{
                        "role": "user", "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                            {"type": "text", "text": "OCR:"}
                        ]
                    }],
                    "temperature": 0.0,
                    "max_tokens": 512
                }

                try:
                    start = time.time()
                    response = await self.client.post(self.endpoint, json=payload)
                    response.raise_for_status()
                    content = response.json()['choices'][0]['message']['content']
                    results.append({"page": page_idx + 1, "content": content, "latency": time.time() - start, "success": True})
                except Exception:
                    results.append({"page": page_idx + 1, "success": False})
            self.queue.task_done()

    async def run_turbo(self, pdf_path: str):
        print(f"🏎️ [Turbo-4060] 开启多核并发流水线模式...")
        doc = fitz.open(pdf_path)
        total_pages = min(len(doc), 50)
        doc.close()
        results = []

        start_time = time.time()
        
        # 1. 启动 OCR 消费者
        workers = [asyncio.create_task(self.ocr_worker(results)) for _ in range(8)]

        # 2. 生产者：利用多进程池进行极速渲染
        loop = asyncio.get_running_loop()
        print(f"🧵 [CPU] 正在调用多核性能进行并发渲染...")
        
        # 建议并发数设为 CPU 逻辑核心数的一半，防止系统卡死
        with ProcessPoolExecutor(max_workers=os.cpu_count() // 2) as executor:
            # 创建所有渲染任务
            render_tasks = [
                loop.run_in_executor(executor, render_pdf_page, pdf_path, i) 
                for i in range(total_pages)
            ]
            
            # 边渲染，边丢入 OCR 队列（实现真正的流水线）
            for coro in asyncio.as_completed(render_tasks):
                page_idx, img_bytes = await coro
                await self.queue.put((page_idx, img_bytes))
                if (len(results) + self.queue.qsize()) % 50 == 0:
                    print(f"   📥 流水线进度: 已投递 {len(results) + self.queue.qsize()}/{total_pages} 页")

        # 3. 结束标志
        for _ in range(8):
            await self.queue.put(None)
        
        await asyncio.gather(*workers)
        await self.queue.join()

        total_time = time.time() - start_time
        success_count = sum(1 for r in results if r.get("success"))
        
        print("\n" + "💎"*20)
        print(f"🏆 最终性能极限报告")
        print(f"  页数: {total_pages} | 成功: {success_count}")
        print(f"  总耗时: {total_time:.2f}s | 速度: {total_pages/total_time:.2f} 页/秒")
        print("💎"*20)

        # 汇总
        results.sort(key=lambda x: x['page'])
        full_md = "\n\n".join([r['content'] for r in results if r.get('success')])
        with open("ocr_ceshi/full_book_turbo.md", "w", encoding="utf-8") as f:
            f.write(full_md)
        print(f"📂 成果已保存至: ocr_ceshi/full_book_turbo.md")

if __name__ == "__main__":
    asyncio.run(GLM4060Turbo().run_turbo("ocr_ceshi/1.pdf"))
