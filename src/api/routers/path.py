"""学习路径路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.schemas.path_schema import PathGenerateRequest, PathStatusUpdate
from src.services import path_service
from src.utils.response import success

router = APIRouter(prefix="/paths", tags=["学习路径"])


@router.get("", summary="获取学习路径列表")
def list_paths(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = path_service.get_path_list(db, current_user.id)
    return success(data, "获取成功")


@router.post("/generate", summary="生成学习路径")
async def generate_path(
    body: PathGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        data = await path_service.generate_path(
            db,
            user_id=current_user.id,
            profile_id=body.profile_id,
            daily_hours=body.daily_hours,
            learning_cycle_days=body.learning_cycle_days,
            goal=body.goal,
        )
    except path_service.PathNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"路径生成失败: {exc}")
    return success(data, "路径已生成")


@router.get("/{path_id}", summary="获取路径详情")
def get_path(
    path_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        data = path_service.get_path_detail(db, path_id, current_user.id)
    except path_service.PathNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return success(data, "获取成功")


@router.put("/{path_id}/status", summary="更新路径状态")
def update_status(
    path_id: int,
    body: PathStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        data = path_service.update_path_status(db, path_id, current_user.id, body.status)
    except path_service.PathNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return success(data, "状态已更新")
