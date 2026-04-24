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

    # 2. AI 引擎 (BYOK)
    LLM_PROVIDER: str = "deepseek"
    LLM_API_KEY: Optional[str] = None
    LLM_BASE_URL: str = "https://api.deepseek.com/v1"
    LLM_MODEL_NAME: str = "deepseek-chat"
   
    
    # VLM 配置 (用于视觉确认)
    # 🏛️ 架构师：默认值仅用于 .env 缺失时的回退，实际值从 .env 读取
    # VLM_API_KEY 是 property (见第 86 行)，自动回退到 EMBEDDING_API_KEY
    VLM_BASE_URL: str = "https://api.siliconflow.cn/v1"
    VLM_MODEL_NAME: str = "Qwen/Qwen2.5-VL-72B-Instruct"  # 硅基流动 72B 高精度版

    # --- 🚀 [V43.7] 全局统一 API 接口 (SiliconFlow 核心) ---
    # 架构师指令：所有的云端能力（VLM, Embedding）统一共用此 Key
    EMBEDDING_API_KEY: Optional[str] = None
    EMBEDDING_BASE_URL: str = "https://api.siliconflow.cn/v1"
    EMBEDDING_MODEL_NAME: str = "BAAI/bge-m3"
    EMBEDDING_MODEL_PATH: str = r"E:\ai_models\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181"
    EMBEDDING_DIMENSION: int = 1024

    # --- 🚀 [V49.0] 联网证人配置 (Tavily) ---
    TAVILY_API_KEY: Optional[str] = None
    TAVILY_MAX_RESULTS: int = 3
    TAVILY_SEARCH_DEPTH: str = "advanced"
    TAVILY_CONCURRENT_LIMIT: int = 5
    TAVILY_FALLBACK_SLEEP_SECONDS: int = 3  # 🚀 [V50.6] 联网失败后休眠秒数

    # --- 🐦 [V52.0] 飞书/Lark 集成配置 ---
    FEISHU_APP_ID: Optional[str] = None
    FEISHU_APP_SECRET: Optional[str] = None
    FEISHU_DEFAULT_CHAT_ID: Optional[str] = None
    FEISHU_BITABLE_TOKEN: Optional[str] = None
    FEISHU_BITABLE_TABLE_ID: Optional[str] = None

    # --- 🚀 [V50.10] 联邦法庭配置 ---
    COURT_SCOUT_QUERY_LIMIT: int = 3  # Scout 拆解查询数量上限
    COURT_CONTEXT_TOC_LIMIT: int = 50  # 上下文 TOC 截取上限
    COURT_AUTHORITY_PEER_REVIEW_BONUS: float = 1.10  # 同行评审加成 10%
    COURT_AUTHORITY_USER_GENERATED_PENALTY: float = 0.90  # 用户生成惩罚 10%
    COURT_AUTHORITY_CROSS_SOURCE_BONUS: float = 1.10  # 跨源印证加成 10%

    # --- 🚀 [V50.11] TOC 验证约束 ---
    TOC_MAX_PAGES_LIMIT: int = 5000  # 最大页数限制
    TOC_MAX_DEPTH_LIMIT: int = 8  # 最大目录层级
    TOC_MAX_ITEMS_LIMIT: int = 1000  # 最大目录项数

    # --- 🚀 [V50.11] 上下文截断配置 ---
    CONTEXT_LOGIC_TAGS_LIMIT: int = 10  # logic_tags 截取上限
    CONTEXT_SELECTED_IDS_LIMIT: int = 5  # Examiner 选择分片上限
    CONTEXT_FALLBACK_CHUNKS: int = 3  # Examiner 兜底分片数
    CONTEXT_COMMIT_QUERY_PREFIX: int = 30  # Git 提交消息查询前缀长度
    CONTEXT_COMMIT_DOC_ID_PREFIX: int = 8  # 文档 ID 前缀长度
    CONTEXT_EVIDENCE_CONTENT_PREFIX: int = 150  # 证据内容截取上限
    CONTEXT_EVIDENCE_REASON_PREFIX: int = 50  # 裁决原因截取上限
    CONTEXT_CHUNK_PREVIEW_KEYWORDS: int = 5  # 切片预览关键词数量
    CONTEXT_CHUNK_PREVIEW_CONTENT: int = 200  # 切片预览内容长度
    CONTEXT_VECTOR_BATCH_TEXT_PREFIX: int = 1500  # 向量嵌入文本截取上限

    # --- 🚀 [V51.1] 冲突裁决配置 ---
    # 🚀 [V51.2] 已弃用：向量过滤被移除（Distributor 负责相关性筛选）
    # CONFLICT_SIMILARITY_THRESHOLD: float = 0.35  # 保留但不再使用
    CONFLICT_SCOUT_RECOMMENDED_MIN: int = 3  # Scout 推荐证据数量下限
    CONFLICT_SCOUT_RECOMMENDED_MAX: int = 12  # Scout 推荐证据数量上限

    @property
    def VLM_API_KEY(self) -> Optional[str]:
        # 自动回退：优先使用 VLM 专用 Key，否则使用全局共用 Key
        return os.getenv("VLM_API_KEY") or self.EMBEDDING_API_KEY

    # --- 🚀 环境自适应推理接口 ---
   
    
    # 🏛️ 架构师指令：从 .env 读取配置（如果有），否则使用默认值
    # 这样既支持动态配置，又保证有合理的回退值
    
    STORAGE_ROOT: str = str(BACKEND_ROOT / "storage")
    TEMP_UPLOADS: str = str(BACKEND_ROOT / "temp_uploads")
    CACHE_DIR: str = "E:/ai_models"

    # 4. 环境与调试

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
