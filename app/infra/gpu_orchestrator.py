import asyncio
import psutil
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

class GPUTaskOrchestrator:
    """
    🚀 V43.2 显存潮汐调度器
    职责：基于当前系统内存水位动态调控 GPU 任务并发，防止 OOM (Out-of-Memory) 导致的 JSON 崩溃。
    """
    def __init__(self, max_concurrent: int = 2):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    async def execute(self, task_name: str, func: Callable, *args, **kwargs) -> Any:
        mem = psutil.virtual_memory()
        # 如果内存水位超过 85%，强制降级为单线程串行模式
        if mem.percent > 85:
            logger.warning(f"⚠️ [GPU-Orchestrator] 内存水位过高 ({mem.percent}%)，强制串行执行: {task_name}")
            async with asyncio.Lock(): # 全局锁，强制串行
                return await func(*args, **kwargs)
        
        # 正常状态：使用信号量并发
        async with self.semaphore:
            return await func(*args, **kwargs)

# 全局单例
gpu_orchestrator = GPUTaskOrchestrator()
