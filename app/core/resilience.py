import asyncio
import time
import functools
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"

class CircuitBreaker:
    """
    🚀 [V22.0] 工业级熔断器
    """
    def __init__(self, failure_threshold=3, recovery_timeout=30):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = CircuitState.CLOSED

    def __call__(self, func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == CircuitState.OPEN:
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                    print("⚡ [CircuitBreaker] 熔断器进入半开状态，尝试恢复...")
                else:
                    raise RuntimeError("🚨 [CircuitBreaker] 熔断器开启，请求被拦截以保护后端。")

            try:
                result = await func(*args, **kwargs)
                if self.state == CircuitState.HALF_OPEN:
                    print("✅ [CircuitBreaker] 恢复成功，熔断器关闭。")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                return result
            except Exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitState.OPEN
                    print(f"🚨 [CircuitBreaker] 连续失败 {self.failure_count} 次，熔断器开启！")
                raise e
        return wrapper

# 默认 OCR 熔断器
ocr_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=15)
