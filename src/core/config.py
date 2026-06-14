"""智学工坊核心配置模块。"""

from pathlib import Path
from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── 应用 ────────────────────────────────────────────────────
    APP_NAME: str = "智学工坊"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ── 服务 ────────────────────────────────────────────────────
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8001

    # ── 数据库 ──────────────────────────────────────────────────
    DATABASE_URL: str = ""

    # ── JWT ─────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "change-this-secret"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 43200  # 30 天

    # ── Dify ────────────────────────────────────────────────────
    DIFY_MOCK_MODE: bool = True

    # ── LLM (DeepSeek) ──────────────────────────────────────────
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.deepseek.com"
    LLM_MODEL: str = "deepseek-chat"
    LLM_TIMEOUT_SECONDS: int = 120
    LLM_TEMPERATURE: float = 0.7

    # ── 跨域 ────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ]

    # ── 上传 ────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 20


settings = Settings()
