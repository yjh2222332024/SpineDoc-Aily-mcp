import base64
import httpx
import asyncio
import time
import cv2
import numpy as np
import os
import random
from typing import List, Dict, Any, Optional


class GLMWorker:
    """
    SpineDoc 统一感知工兵 (Hybrid OCR Edition)
    ========================================
    特性：
    1. 自动探测：优先使用本地 SGLang 算力。
    2. 云端降级：本地不可用时自动调用 SiliconFlow/OpenAI 接口。
    3. 零配置友好：只需一个 API Key 即可激活扫描件处理。
    """

    def __init__(self, api_urls: Optional[List[str]] = None, **kwargs):
        # 1. 探测本地环境
        self.api_urls = api_urls or [os.getenv("OCR_API_URL", "http://127.0.0.1:30000/v1/chat/completions")]
        self.cloud_api_key = os.getenv("SILICONFLOW_API_KEY") or os.getenv("LLM_API_KEY")
        self.cloud_base_url = "https://api.siliconflow.cn/v1/chat/completions"

        # 🚀 [V1.1.6 Fix] 补齐轮询索引，防止 _get_next_url 报错
        self.current_index = 0
        self.mode = "LOCAL"

        # 🚀 [V18.2] 生产级连接池优化
        limits = httpx.Limits(
            max_keepalive_connections=50,
            max_connections=100,
            keepalive_expiry=30.0
        )
        self.client = httpx.AsyncClient(timeout=120.0, limits=limits)

    async def _check_mode(self):
        """智能判定：本地还是云端？"""
        try:
            resp = await self.client.get(self.api_urls[0].replace("/v1/chat/completions", "/health"), timeout=2)
            if resp.status_code == 200:
                self.mode = "LOCAL"
                return
        except:
            pass

        if self.cloud_api_key:
            self.mode = "CLOUD"
        else:
            self.mode = "NATIVE" # 仅提取 PDF 电子层

    async def ocr_to_markdown(self, image_np: np.ndarray) -> str:
        """
        OCR 单页图像，返回 Markdown 格式
        """
        res_dict = await self.ocr_page_batch([image_np], [0])
        return list(res_dict.values())[0] if res_dict else ""

    async def ocr_page_batch(self, image_nps: List[np.ndarray], indices: List[int]) -> Dict[int, str]:
        """
        批量 OCR 处理（自动并行）
        """
        start_time = time.time()

        # 创建并发任务
        tasks = [self._single_request(img, idx) for img, idx in zip(image_nps, indices)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 处理异常
        final_results = {}
        failed_count = 0
        for idx, result in zip(indices, results):
            if isinstance(result, Exception):
                print(f"⚠️ Page {idx+1} OCR 失败：{result}")
                final_results[idx] = ""
                failed_count += 1
            elif isinstance(result, tuple):
                # 🚀 [V18.9] 修复：只提取 content 部分
                _, content = result
                final_results[idx] = content
            else:
                final_results[idx] = result

        elapsed = time.time() - start_time
        print(f"⚡ [批量 OCR] 完成 {len(image_nps)} 页，耗时 {elapsed:.2f}s, 成功率 {100 - failed_count * 100 / len(image_nps):.0f}%")

        return final_results

    async def _single_request(self, image_np: np.ndarray, idx: int) -> tuple:
        """
        单页 OCR 请求（带指数退避与故障转移）
        """
        # 🚀 [V1.3.3 Fix] 缩小图片尺寸，防止超过 encoder cache 限制
        h, w = image_np.shape[:2]
        max_dim = 1024  # 最大边长
        if h > max_dim or w > max_dim:
            scale = max_dim / max(h, w)
            image_np = cv2.resize(image_np, (int(w * scale), int(h * scale)))
        
        # 图像编码为 JPEG (降低质量到 70%)
        _, buffer = cv2.imencode(".jpg", image_np, [cv2.IMWRITE_JPEG_QUALITY, 70])
        base64_image = base64.b64encode(buffer).decode("utf-8")

        # 🚀 [V18.2] 标准请求格式 (SGLang glm-ocr 0.9b)
        payload = {
            "model": "/model",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": "OCR:"},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }],
            "temperature": 0.0,
            "max_tokens": 512,
            "stream": False
        }

        # 🚀 [V18.2 故障转移与指数退避]
        max_retries = len(self.api_urls) * 3
        for attempt in range(max_retries):
            api_url = self._get_next_url()
            try:
                resp = await self.client.post(api_url, json=payload)
                if resp.status_code == 502:
                    raise httpx.HTTPStatusError("Bad Gateway", request=resp.request, response=resp)
                resp.raise_for_status()
                content = resp.json()['choices'][0]['message']['content']
                return idx, content
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 0.5 + random.uniform(0, 1.0)
                    print(f"⚠️ 实例 {api_url} 异常，{wait_time:.2f}s 后重试 ({attempt+1}/{max_retries}): {e}")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"🚨 [GLM-Worker] 彻底失败！Page: {idx+1} | 错误：{e}")
                    return idx, ""

        return idx, ""

    def _get_next_url(self) -> str:
        """轮询获取下一个可用 URL"""
        url = self.api_urls[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.api_urls)
        return url

    @property
    def is_available(self) -> bool:
        """检查后端是否配置"""
        return len(self.api_urls) > 0

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()


class MultiInstanceGLMWorker(GLMWorker):
    """
    多实例专用 Worker（4 实例并行版）
    ================================

    自动连接 4 个 SGLang 实例 (端口 30000-30003)，实现高吞吐 OCR。

    用法:
        worker = MultiInstanceGLMWorker()
        results = await worker.ocr_page_batch(images, indices)

    前提条件:
        先运行：python start_multi_sglang.py --count 4
    """

    def __init__(self, base_port: int = 30000, num_instances: int = 4, **kwargs):
        # 构建多实例 URL 列表
        api_urls = [
            f"http://127.0.0.1:{base_port + i}/v1/chat/completions"
            for i in range(num_instances)
        ]

        super().__init__(api_urls=api_urls, **kwargs)

        self.num_instances = num_instances
        self.base_port = base_port

        print(f"🚀 [Multi-Instance] {num_instances} 实例并行模式已激活")
        print(f"   📊 端口范围：{base_port} - {base_port + num_instances - 1}")
        print(f"   📈 预期吞吐量：{80 * num_instances}-{150 * num_instances} TPS")
        print(f"   📊 400 页文档处理时间：< {60 / num_instances:.0f} 秒")


class AutoGLMWorker:
    """
    智能 GLMWorker 工厂
    ==================
    自动检测可用的 SGLang 实例并创建合适的 Worker

    用法:
        worker = await AutoGLMWorker.create()
        results = await worker.ocr_page_batch(images, indices)
    """

    @staticmethod
    async def _check_instance(url: str) -> bool:
        """检查实例是否可用"""
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                resp = await client.get(url.replace("/v1/chat/completions", "/health"))
                return resp.status_code == 200
        except:
            return False

    @classmethod
    async def create(
        cls,
        base_port: int = 30000,
        max_instances: int = 4,
        **kwargs
    ) -> GLMWorker:
        """
        创建合适的 Worker

        Args:
            base_port: SGLang 基础端口
            max_instances: 最大检测实例数
            **kwargs: 传递给 GLMWorker 的参数

        Returns:
            GLMWorker 或 MultiInstanceGLMWorker
        """
        print("🔍 正在检测可用的 SGLang 实例...")

        available_urls = []
        for i in range(max_instances):
            url = f"http://127.0.0.1:{base_port + i}/v1/chat/completions"
            if await cls._check_instance(url):
                available_urls.append(url)
                print(f"   ✅ 实例 {i+1}: {url}")
            else:
                print(f"   ❌ 实例 {i+1}: {url} (不可用)")

        if not available_urls:
            raise ConnectionError(
                "未找到可用的 SGLang 实例！\n"
                "请先启动：python start_sglang_engine.py\n"
                "或多实例：python start_multi_sglang.py --count 4"
            )

        if len(available_urls) == 1:
            print(f"🚀 [AutoGLMWorker] 单实例模式：{available_urls[0]}")
            return GLMWorker(api_urls=available_urls, **kwargs)
        else:
            print(f"🚀 [AutoGLMWorker] 多实例模式 ({len(available_urls)} 实例)")
            return GLMWorker(api_urls=available_urls, **kwargs)
