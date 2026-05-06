from pydantic_settings import BaseSettings
from pydantic import Field
import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# --- 路径锚定：顶级架构师的绝对基准 ---
# APP_ROOT = .../backend/app
APP_ROOT = Path(__file__).resolve().parent.parent
# BACKEND_ROOT = .../backend
BACKEND_ROOT = APP_ROOT.parent
# PROJECT_ROOT = .../
PROJECT_ROOT = BACKEND_ROOT.parent

#  [V62.0] 显式加载驱动：确保 Windows 环境下的确定性
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)

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

    # 2. AI 引擎 (BYOK) -  [V61.0] 豆包 2.0 标准契约
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    LLM_ENDPOINT: Optional[str] = None

    @property
    def REAL_LLM_KEY(self) -> Optional[str]:
        return self.LLM_API_KEY

    @property
    def REAL_LLM_MODEL(self) -> str:
        """如果提供了 Endpoint，则优先使用它作为模型 ID"""
        return self.LLM_ENDPOINT or "doubao-2.0"
   
    
    # VLM 配置 (用于视觉确认)
    VLM_BASE_URL: str = "https://api.siliconflow.cn/v1"
    VLM_MODEL_NAME: str = "Qwen/Qwen2.5-VL-72B-Instruct"

    # ---  [V43.7] 全局统一 API 接口 (SiliconFlow 核心) ---
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_BASE_URL: str = "https://api.siliconflow.cn/v1"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024

    # ---  [V110.0] 联网检索配置 (智谱 Web Search API) ---
    ZHIPU_API_KEY: Optional[str] = None
    ZHIPU_SEARCH_ENGINE: str = "search_pro"       # search_std / search_pro / search_pro_sogou / search_pro_quark
    ZHIPU_MAX_RESULTS: int = 5
    ZHIPU_CONTENT_SIZE: str = "high"              # low / medium / high

    # ---  [V52.0] 飞书/Lark 集成配置 ---
    FEISHU_APP_ID: Optional[str] = None
    FEISHU_APP_SECRET: Optional[str] = None
    FEISHU_DEFAULT_CHAT_ID: Optional[str] = None
    FEISHU_BITABLE_TOKEN: Optional[str] = None
    FEISHU_BITABLE_TABLE_ID: Optional[str] = None

    # ---  [V290.0] LLM 并发控制 ---
    LLM_MAX_CONCURRENCY: int = Field(default=5, ge=1, le=20, description="LLM 调用最大并发数")

    # OCR 并发控制（ocr_process_utils.py 使用）
    OCR_MAX_CONCURRENCY: int = 1

    # ---  [V50.10] 检索协调器配置 ---
    COURT_AUTHORITY_PEER_REVIEW_BONUS: float = 1.10
    COURT_AUTHORITY_USER_GENERATED_PENALTY: float = 0.90

    # ---  [V51.1] 冲突裁决配置 ---
    CONTEXT_FALLBACK_CHUNKS: int = 3
    CONTEXT_COMMIT_DOC_ID_PREFIX: int = 8
    CONTEXT_EVIDENCE_CONTENT_PREFIX: int = 150
    CONTEXT_CHUNK_PREVIEW_CONTENT: int = 200

    # ARK（豆包 OCR 熔炼）
    ARK_API_KEY: Optional[str] = None
    ARK_BASE_URL: Optional[str] = None
    ARK_ENDPOINT: Optional[str] = None

    # 飞书 Wiki
    FEISHU_WIKI_NODE_ID: str = ""

    # Aily 桥接
    FEISHU_AILY_TOKEN: Optional[str] = None

    # A-MEM Bitable
    FEISHU_BITABLE_MEMORY_TABLE_ID: Optional[str] = None
    FEISHU_BITABLE_CHUNK_TABLE_ID: Optional[str] = None
    FEISHU_BITABLE_TOC_TABLE_ID: Optional[str] = None
    FEISHU_BITABLE_GALAXY_TABLE_ID: Optional[str] = None

    # ---  环境自适应推理接口 ---
   
    
    #  架构师指令：从 .env 读取配置（如果有），否则使用默认值
    # 这样既支持动态配置，又保证有合理的回退值
    
    STORAGE_ROOT: str = str(BACKEND_ROOT / "storage")
    TEMP_UPLOADS: str = str(BACKEND_ROOT / "temp_uploads")
    CACHE_DIR: str = "E:/ai_models"

    # 4. 环境与调试

    model_config = {
        #  架构师对齐：强制指向项目根目录的 .env，确保 Docker 与本地环境共用一套 Key
        "env_file": str(BACKEND_ROOT.parent / ".env"),
        "case_sensitive": True,
        "extra": "ignore"
    }

settings = Settings()

# 自动创建必要物理目录
os.makedirs(settings.STORAGE_ROOT, exist_ok=True)
os.makedirs(settings.TEMP_UPLOADS, exist_ok=True)
