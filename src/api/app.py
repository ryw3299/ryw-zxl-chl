"""FastAPI application entry point for the ChaoXingAgent backend service.

Run in development mode:
    DEBUG=true uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.api.config import settings
from src.api.deps import generate_request_id
from src.api.middleware import SignatureVerifyMiddleware
from src.api.models.database import init_db
from src.api.routers import auth, knowledge_base, lesson, platform, progress, qa
from src.utils.paths import paths

TAGS_METADATA = [
    {
        "name": "智课生成",
        "description": "智课智能生成模块 — 一键流水线生成、课件解析、脚本生成、PPT 渲染、语音合成、教师编辑。",
    },
    {
        "name": "实时问答",
        "description": "多模态实时问答模块 — 文字/语音问答交互、上下文关联解答、多轮交互。",
    },
    {
        "name": "学习进度",
        "description": "学习进度智能适配模块 — 学习进度追踪、理解程度评估、讲授节奏调整。",
    },
    {
        "name": "平台对接",
        "description": "平台对接预留接口 — 外部教育平台课程同步、用户同步，支持跨平台集成。",
    },
    {
        "name": "系统",
        "description": "系统健康检查与运维接口。",
    },
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Make sure every runtime directory exists before the first request.
    paths.ensure()
    init_db()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "基于泛雅平台的 AI 互动智课生成与实时问答系统后端服务。\n\n"
        "## 核心模块\n\n"
        "- **智课生成** — 一键流水线 / 课件解析 → 脚本生成 → PPT 渲染 → 语音合成\n"
        "- **实时问答** — 文字/语音提问 → 上下文关联解答 → 多轮交互\n"
        "- **进度适配** — 学习进度追踪 → 理解程度分析 → 讲授节奏调整\n"
        "- **平台对接** — 课程/用户同步 → 跨平台集成\n\n"
        "## 接口规范\n\n"
        "- 数据格式：JSON / UTF-8\n"
        "- 签名验证：`enc = MD5(参数有序拼接 + staticKey + time)`\n"
        "- 版本控制：URL 含版本号 `/api/v1`\n"
        "- 响应格式：`{code, msg, data, requestId}`\n"
    ),
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=TAGS_METADATA,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SignatureVerifyMiddleware)

app.include_router(lesson.router, prefix=settings.API_V1_PREFIX)
app.include_router(qa.router, prefix=settings.API_V1_PREFIX)
app.include_router(progress.router, prefix=settings.API_V1_PREFIX)
app.include_router(platform.router, prefix=settings.API_V1_PREFIX)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(knowledge_base.router, prefix="/internal")


# ── built-in test panel (single-file HTML) ──────────────────────────

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_TEST_PANEL_DIR = _PROJECT_ROOT / "frontend" / "test_panel"
if _TEST_PANEL_DIR.is_dir():
    app.mount(
        "/panel",
        StaticFiles(directory=str(_TEST_PANEL_DIR), html=True),
        name="test_panel",
    )


@app.get("/", include_in_schema=False)
def root_index():
    """Convenience landing page that surfaces the test panel + Swagger."""
    panel_index = _TEST_PANEL_DIR / "index.html"
    if panel_index.exists():
        return FileResponse(str(panel_index))
    return JSONResponse(
        content={
            "service": settings.PROJECT_NAME,
            "docs": "/docs",
            "panel": "/panel",
            "health": "/health",
        }
    )


# ── global exception handlers ───────────────────────────────────────


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "msg": str(exc.detail),
            "data": None,
            "requestId": generate_request_id(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "msg": "服务端内部错误",
            "data": None,
            "requestId": generate_request_id(),
        },
    )


# ── system endpoints ────────────────────────────────────────────────


@app.get(
    "/health",
    tags=["系统"],
    summary="健康检查",
    description="检查服务运行状态。",
)
def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "debug": settings.DEBUG,
        "paths": paths.as_dict(),
    }
