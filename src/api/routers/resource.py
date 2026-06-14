"""平台资源路由。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.deps import get_current_user, get_optional_user
from src.models.user import User
from src.services import resource_service
from src.utils.response import success

router = APIRouter(prefix="/resources", tags=["资源中心"])


@router.get("", summary="获取资源列表")
def list_resources(
    resource_type: str = Query("", alias="resource_type"),
    direction: str = Query(""),
    difficulty: str = Query(""),
    keyword: str = Query(""),
    page: int = Query(1),
    page_size: int = Query(20),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    filters = {
        "resource_type": resource_type,
        "direction": direction,
        "difficulty": difficulty,
        "keyword": keyword,
        "page": page,
        "page_size": page_size,
    }
    items, total = resource_service.get_resource_list(db, filters)
    return success({"items": items, "total": total, "page": page, "page_size": page_size}, "获取成功")


@router.get("/{resource_id}", summary="获取资源详情")
def get_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    try:
        data = resource_service.get_resource_detail(db, resource_id)
    except resource_service.ResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return success(data, "获取成功")


@router.post("/{resource_id}/view", summary="记录资源查看")
def record_view(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    return success(None, "记录成功")
