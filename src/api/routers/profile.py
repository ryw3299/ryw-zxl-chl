"""画像路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.schemas.profile_schema import ProfileInitRequest
from src.services import profile_service
from src.utils.response import success

router = APIRouter(prefix="/profile", tags=["画像"])


@router.get("/me", summary="获取当前学生画像")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        data = profile_service.get_latest_profile(db, current_user.id)
    except profile_service.ProfileNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return success(data, "获取成功")


@router.post("/init", summary="初始化画像对话")
async def init_profile(
    body: ProfileInitRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    chat_data = [m.model_dump() for m in body.chat_history]
    try:
        data = await profile_service.init_profile(
            db, current_user.id, chat_data, body.conversation_id
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"画像生成失败: {exc}")
    msg = data.get("frontend_message") or (
        "画像已生成" if data.get("profile_ready") else "已更新画像信息"
    )
    return success(data, msg)


@router.get("/init-state", summary="获取最近一次未完成画像初始化会话")
def get_init_state(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = profile_service.get_latest_init_state(db, current_user.id)
    return success(data, "获取成功")


@router.get("/history", summary="获取画像历史版本")
def get_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = profile_service.get_profile_history(db, current_user.id)
    return success(data, "获取成功")
