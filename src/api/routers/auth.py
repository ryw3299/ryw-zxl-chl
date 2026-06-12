"""Routers for local username/password authentication."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.deps import generate_request_id
from src.api.models.database import get_db
from src.api.response_models import ApiResponse, ErrorResponse
from src.api.services import auth_service

router = APIRouter(prefix="/auth", tags=["认证"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "参数错误"},
    401: {"model": ErrorResponse, "description": "认证失败"},
    409: {"model": ErrorResponse, "description": "账号冲突"},
}


class RegisterRequest(BaseModel):
    userId: str = Field(..., min_length=2, max_length=64, description="登录账号")
    password: str = Field(..., min_length=6, max_length=128, description="登录密码")
    role: str = Field("student", description="注册角色，当前仅支持 student")
    userName: str = Field("", max_length=128, description="显示名称")
    schoolId: str = Field("", max_length=64, description="学校 ID")
    enc: str = Field("", description="签名信息")
    time: str = Field("", description="当前时间")


class LoginRequest(BaseModel):
    userId: str = Field(..., min_length=2, max_length=64, description="登录账号")
    password: str = Field(..., min_length=6, max_length=128, description="登录密码")
    role: str = Field("", description="登录入口角色: student/teacher")
    enc: str = Field("", description="签名信息")
    time: str = Field("", description="当前时间")


class AuthUserInfo(BaseModel):
    userId: str = ""
    userName: str = ""
    role: str = "student"
    schoolId: str = ""


class AuthData(BaseModel):
    authToken: str = ""
    userInfo: AuthUserInfo = Field(default_factory=AuthUserInfo)


def _success(data: dict, msg: str) -> dict:
    return {
        "code": 200,
        "msg": msg,
        "data": data,
        "requestId": generate_request_id(),
    }


def _bearer_token(authorization: Optional[str]) -> str:
    value = str(authorization or "").strip()
    if value.lower().startswith("bearer "):
        return value[7:].strip()
    return value


@router.post(
    "/register",
    response_model=ApiResponse[AuthData],
    responses=_ERROR_RESPONSES,
    summary="注册学生账号",
)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    try:
        data = auth_service.register_user(
            db,
            user_id=body.userId,
            password=body.password,
            role=body.role,
            user_name=body.userName,
            school_id=body.schoolId,
        )
    except auth_service.AuthConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except auth_service.AuthInvalidError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _success(data, "注册成功")


@router.post(
    "/login",
    response_model=ApiResponse[AuthData],
    responses=_ERROR_RESPONSES,
    summary="登录本地账号",
)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    try:
        data = auth_service.login_user(
            db,
            user_id=body.userId,
            password=body.password,
            role=body.role,
        )
    except auth_service.AuthInvalidError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return _success(data, "登录成功")


@router.get(
    "/me",
    response_model=ApiResponse[AuthData],
    responses=_ERROR_RESPONSES,
    summary="获取当前用户",
)
def me(
    authorization: Optional[str] = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    try:
        data = auth_service.get_user_by_token(db, _bearer_token(authorization))
    except auth_service.AuthInvalidError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    return _success(data, "获取成功")
