"""学习任务路由。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.supplement import StudyTask
from src.models.user import User
from src.utils.response import success

router = APIRouter(prefix="/tasks", tags=["学习任务"])


@router.get("", summary="获取今日任务列表")
def list_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = (
        db.query(StudyTask)
        .filter(StudyTask.user_id == current_user.id)
        .order_by(StudyTask.created_at.desc())
        .limit(20)
        .all()
    )
    data = [
        {
            "id": t.id,
            "title": t.title,
            "duration_minutes": t.duration_minutes,
            "is_done": t.is_done,
            "resource_id": t.resource_id,
            "created_at": str(t.created_at),
        }
        for t in tasks
    ]
    return success(data, "获取成功")


@router.post("", summary="创建任务")
def create_task(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = StudyTask(
        user_id=current_user.id,
        title=body.get("title", ""),
        duration_minutes=body.get("duration_minutes"),
        resource_id=body.get("resource_id"),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return success({"id": task.id, "title": task.title}, "任务已创建")


@router.put("/{task_id}/toggle", summary="切换任务完成状态")
def toggle_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(StudyTask).filter(StudyTask.id == task_id, StudyTask.user_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.is_done = not task.is_done
    db.commit()
    return success({"id": task.id, "is_done": task.is_done}, "状态已更新")
