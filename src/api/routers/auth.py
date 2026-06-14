"""认证与用户路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.schemas.user_schema import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserInfo,
    UserUpdateRequest,
)
from src.services import auth_service
from src.utils.response import success

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", summary="注册学生账号")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    try:
        data = auth_service.register_user(
            db, username=body.username, password=body.password, email=body.email
        )
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return success(data, "注册成功")


@router.post("/login", summary="登录")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    try:
        data = auth_service.login_user(
            db, username=body.username, password=body.password
        )
    except auth_service.AuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc))
    return success(data, "登录成功")


@router.get("/me", summary="获取当前用户信息")
def me(current_user: User = Depends(get_current_user)):
    return success(auth_service.get_user_info(current_user), "获取成功")


router_user = APIRouter(prefix="/user", tags=["用户"])


@router_user.get("/me", summary="获取当前用户信息")
def get_me(current_user: User = Depends(get_current_user)):
    return success(auth_service.get_user_info(current_user), "获取成功")


@router_user.put("/me", summary="更新用户信息")
def update_me(
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.email:
        current_user.email = body.email
        db.commit()
    return success(auth_service.get_user_info(current_user), "更新成功")
