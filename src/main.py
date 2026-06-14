"""智学工坊 FastAPI 应用入口。"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.config import settings
from src.core.database import init_db
from src.core.deps import generate_request_id


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="基于大模型的工科生个性化学习资源生成与多智能体学习辅助系统",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── 全局异常处理 ────────────────────────────────────────────────


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


# ── 路由注册 ────────────────────────────────────────────────────

from src.api.routers import auth, profile, path, resource, generated_resource, event, assistant, quiz, task, announcement, study_record  # noqa: E402

prefix = settings.API_V1_PREFIX
app.include_router(auth.router, prefix=prefix)
app.include_router(profile.router, prefix=prefix)
app.include_router(path.router, prefix=prefix)
app.include_router(resource.router, prefix=prefix)
app.include_router(generated_resource.router, prefix=prefix)
app.include_router(event.router, prefix=prefix)
app.include_router(assistant.router, prefix=prefix)
app.include_router(quiz.router, prefix=prefix)
app.include_router(task.router, prefix=prefix)
app.include_router(announcement.router, prefix=prefix)
app.include_router(study_record.router, prefix=prefix)


# ── 系统端点 ────────────────────────────────────────────────────


@app.get("/health", tags=["系统"])
def health_check():
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "debug": settings.DEBUG,
    }
