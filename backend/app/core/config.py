from pydantic_settings import BaseSettings
import os
from uuid import UUID
from typing import Optional
from pathlib import Path

# --- 路径锚定：顶级架构师的绝对基准 ---
# APP_ROOT = .../backend/app
APP_ROOT = Path(__file__).resolve().parent.parent
# BACKEND_ROOT = .../backend
BACKEND_ROOT = APP_ROOT.parent

class Settings(BaseSettings):
    """
    【架构师级配置】：支持动态合成连接串，适配多环境运行。
    """
    PROJECT_NAME: str = "SpineDoc"
    
    # 1. 数据库零件 (从 .env 读取)
    DB_USER: str = "spinedoc"
    DB_PASSWORD: str = "spinedoc123"
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 5432
    DB_NAME: str = "spinedoc"

    @property
    def DATABASE_URL(self) -> str:
        # 优先读取系统直接注入的 DATABASE_URL (Docker 模式)，否则动态合成
        env_url = os.getenv("DATABASE_URL")
        if env_url: return env_url
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # 2. Redis 零件
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = "dPYgQR+yWRLs/f8Y/WS8+XSrceUrXRwl"

    @property
    def REDIS_URL(self) -> str:
        env_url = os.getenv("REDIS_URL")
        if env_url: return env_url
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    # 2. AI 引擎 (BYOK)
    LLM_PROVIDER: str = "deepseek"
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL_NAME: str = "deepseek-chat"
    AI_TIMEOUT: int = 300  # 🚀 [架构师提示] 默认 5 分钟超时，适配长文档解析
    OCR_USE_GPU: bool = True  # 🚀 [架构师提示] 默认开启 GPU OCR，独显用户的福音
    
    # VLM 配置 (用于视觉确认)
    VLM_API_KEY: Optional[str] = None
    VLM_BASE_URL: str = "https://api.siliconflow.cn/v1"
    VLM_MODEL_NAME: str = "Qwen/Qwen3-VL-8B-Instruct"
    
    # OCR策略配置
    OCR_STRATEGY: str = "adaptive"  # local_only, cloud_first, fallback, adaptive, batch_mode
    OCR_CLOUD_PROVIDER: str = "deepseek"  # glm, deepseek, alibaba, tencent
    OCR_LOCAL_MAX_PAGES: int = 50  # 本地OCR最大页数，超过则转云端
    OCR_CLOUD_MIN_CONFIDENCE: float = 0.8  # 云端OCR最小置信度
    
    # 云端OCR配置
    GLM_OCR_API_KEY: Optional[str] = None
    DEEPSEEK_OCR_API_KEY: Optional[str] = None
    ALIBABA_OCR_ACCESS_KEY: Optional[str] = None
    ALIBABA_OCR_ACCESS_SECRET: Optional[str] = None
    TENCENT_OCR_SECRET_ID: Optional[str] = None
    TENCENT_OCR_SECRET_KEY: Optional[str] = None
    
    # 性能配置
    OCR_MAX_CONCURRENT_REQUESTS: int = 5  # 云端OCR最大并发请求数
    OCR_REQUEST_TIMEOUT: int = 30  # OCR请求超时时间(秒)

    # --- 🚀 [V43.7] 全局统一 API 接口 (SiliconFlow 核心) ---
    # 架构师指令：所有的云端能力（VLM, Embedding）统一共用此 Key
    EMBEDDING_API_KEY: Optional[str] = None
    
    # VLM 配置 (Qwen3 高精度视觉专家)
    VLM_BASE_URL: str = "https://api.siliconflow.cn/v1"
    VLM_MODEL_NAME: str = "Qwen/Qwen3-VL-8B-Instruct"
    
    @property
    def VLM_API_KEY(self) -> Optional[str]:
        # 自动回退：优先使用 VLM 专用 Key，否则使用全局共用 Key
        return os.getenv("VLM_API_KEY") or self.EMBEDDING_API_KEY

    # --- 🚀 环境自适应推理接口 ---
    @property
    def SLM_API_URL(self) -> str:
        url = os.getenv("SLM_API_URL", "http://127.0.0.1:11434/v1")
        # 🏛️ 顶级架构师：自动纠正宿主机访问容器域名的错误
        if "slm" in url and not self.IS_IN_DOCKER:
            return "http://127.0.0.1:11434/v1"
        return url
    
    # 🏛️ 架构师指令：从 .env 读取配置（如果有），否则使用默认值
    # 这样既支持动态配置，又保证有合理的回退值
    
    STORAGE_ROOT: str = str(BACKEND_ROOT / "storage")
    TEMP_UPLOADS: str = str(BACKEND_ROOT / "temp_uploads")
    
    # 4. 环境与调试
    DEV_MODE: bool = True
    DEV_USER_ID: UUID = UUID("00000000-0000-0000-0000-000000000001") 
    DEV_WORKSPACE_ID: UUID = UUID("00000000-0000-0000-0000-000000000002")

    model_config = {
        # 🏛️ 架构师对齐：强制指向项目根目录的 .env，确保 Docker 与本地环境共用一套 Key
        "env_file": str(BACKEND_ROOT.parent / ".env"),
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings()

# 自动创建必要物理目录
os.makedirs(settings.STORAGE_ROOT, exist_ok=True)
os.makedirs(settings.TEMP_UPLOADS, exist_ok=True)
