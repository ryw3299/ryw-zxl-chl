import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_SQLITE_PATH = _PROJECT_ROOT / "data" / "runtime" / "chaoxing_dev.db"
_DEFAULT_RUNTIME_DIR = _PROJECT_ROOT / "data" / "runtime"


class Settings(BaseSettings):
    """All application settings, sourced from ``.env`` + environment.

    Runtime paths default to ``<project_root>/data/runtime/...`` so that
    repo-tracked sample data stays cleanly separated from generated
    artifacts.  Any individual path can still be overridden via env.
    """

    PROJECT_NAME: str = "知微智课"
    API_V1_PREFIX: str = "/api/v1"
    # Default to DEBUG so local testing skips signature verification.
    DEBUG: bool = True

    # MySQL is the preferred backend; SQLite is the zero-config dev fallback.
    DATABASE_URL: str = Field(default=f"sqlite:///{_DEFAULT_SQLITE_PATH}")
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800

    STATIC_KEY: str = Field(default="chaoxing_default_static_key")
    SIGNATURE_TIMEOUT_SECONDS: int = 300

    # ── runtime paths (auto-resolved by src.utils.paths) ───────────
    RUNTIME_DIR: str = Field(default=str(_DEFAULT_RUNTIME_DIR))
    UPLOAD_DIR: str = Field(default=str(_DEFAULT_RUNTIME_DIR / "uploads"))
    AUDIO_DIR: str = Field(default=str(_DEFAULT_RUNTIME_DIR / "audio"))
    RENDER_DIR: str = Field(default=str(_DEFAULT_RUNTIME_DIR / "renders"))
    LOG_DIR: str = Field(default=str(_DEFAULT_RUNTIME_DIR / "logs"))
    RAG_INDEX_DIR: str = Field(default=str(_PROJECT_ROOT / "data" / "rag_indices"))
    WORKSPACE_DIR: str = Field(default=str(_PROJECT_ROOT / "ChaoXingAgentWorkspace"))
    SESSION_DB_PATH: str = Field(default=str(_DEFAULT_RUNTIME_DIR / "memory" / "student_sessions.db"))
    HISTORY_DB_PATH: str = Field(default=str(_DEFAULT_RUNTIME_DIR / "memory" / "student_qa_history.db"))

    # ── external services ──────────────────────────────────────────
    ASR_PROVIDER: str = "openai"
    ASR_BASE_URL: str = "https://api.siliconflow.cn/v1"
    ASR_API_KEY: str = ""
    ASR_MODEL: str = "FunAudioLLM/SenseVoiceSmall"
    ASR_TIMEOUT_SECONDS: int = 30

    LLM_ENV_PATH: Optional[str] = None

    # Agent backend switch: "claude" (default) or "openhands".
    STUDENT_AGENT_BACKEND: str = "claude"

    CORS_ORIGINS: list[str] = ["*"]

    model_config = {"env_file": str(_PROJECT_ROOT / ".env"), "extra": "ignore"}

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug_value(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
                return True
            if normalized in {"0", "false", "no", "off", "release", "prod", "production"}:
                return False
        return value


settings = Settings()


# Make sure the SQLite parent directory exists when DATABASE_URL points to a
# local SQLite file (typical local-test path).
if settings.DATABASE_URL.startswith("sqlite"):
    try:
        sqlite_target = settings.DATABASE_URL.split("///", 1)[1]
        Path(sqlite_target).parent.mkdir(parents=True, exist_ok=True)
    except (IndexError, OSError):
        # Malformed URL or filesystem error — let the engine raise later.
        pass

# Propagate the agent backend selection to the environment so that the
# ``src/agents/student/__init__.py`` switch picks it up at import time.
os.environ.setdefault("STUDENT_AGENT_BACKEND", settings.STUDENT_AGENT_BACKEND)
