"""生成资源路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.user import User
from src.schemas.resource_schema import GeneratedResourceRequest
from src.services import resource_service
from src.utils.response import success

router = APIRouter(prefix="/generated-resources", tags=["生成资源"])


@router.post("/generate", summary="生成个性化资源")
async def generate_resource(
    body: GeneratedResourceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        data = await resource_service.generate_resource_core(
            db, current_user.id, body.model_dump()
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"资源生成失败: {exc}")
    return success(data, "资源已生成")


@router.get("", summary="获取生成资源列表")
def list_generated(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = resource_service.get_generated_resources(db, current_user.id)
    return success(data, "获取成功")


@router.get("/{resource_id}", summary="获取生成资源详情")
def get_generated(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        data = resource_service.get_generated_resource_detail(db, resource_id, current_user.id)
    except resource_service.ResourceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return success(data, "获取成功")
