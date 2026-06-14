"""学习事件与知识点掌握度路由。"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.event import KnowledgeMastery, LearningEvent
from src.models.user import User
from src.schemas.event_schema import BatchEventsRequest, EventCreateRequest
from src.utils.response import success

router = APIRouter(prefix="/events", tags=["学习行为"])


@router.post("", summary="上报学习行为事件")
def create_event(
    body: EventCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = LearningEvent(
        user_id=current_user.id,
        event_type=body.event_type,
        resource_id=body.resource_id,
        page_id=body.page_id,
        knowledge_point=body.knowledge_point,
        event_data=body.event_data,
    )
    db.add(event)
    db.commit()
    return success(None, "记录成功")


@router.post("/batch", summary="批量上报学习行为事件")
def batch_events(
    body: BatchEventsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for e in body.events:
        event = LearningEvent(
            user_id=current_user.id,
            event_type=e.event_type,
            resource_id=e.resource_id,
            page_id=e.page_id,
            knowledge_point=e.knowledge_point,
            event_data=e.event_data,
        )
        db.add(event)
    db.commit()
    return success(None, "批量记录成功")


@router.get("/me", summary="获取个人学习事件")
def get_my_events(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    events = (
        db.query(LearningEvent)
        .filter(LearningEvent.user_id == current_user.id)
        .order_by(LearningEvent.created_at.desc())
        .limit(50)
        .all()
    )
    data = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "knowledge_point": e.knowledge_point,
            "event_data": e.event_data,
            "created_at": str(e.created_at),
        }
        for e in events
    ]
    return success(data, "获取成功")


@router.get("/mastery/me", summary="获取知识点掌握度")
def get_mastery(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    records = (
        db.query(KnowledgeMastery)
        .filter(KnowledgeMastery.user_id == current_user.id)
        .all()
    )
    data = [
        {
            "knowledge_point": r.knowledge_point,
            "mastery_score": r.mastery_score,
            "confidence": r.confidence,
            "updated_at": str(r.updated_at),
        }
        for r in records
    ]
    return success(data, "获取成功")
