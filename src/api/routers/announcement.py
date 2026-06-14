"""公告路由。"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.models.supplement import Announcement
from src.utils.response import success

router = APIRouter(prefix="/announcements", tags=["公告"])


@router.get("", summary="获取公告列表")
def list_announcements(db: Session = Depends(get_db)):
    announcements = (
        db.query(Announcement)
        .filter(Announcement.is_active == True)
        .order_by(Announcement.created_at.desc())
        .limit(10)
        .all()
    )
    data = [
        {
            "id": a.id,
            "title": a.title,
            "description": a.description,
            "type": a.type,
            "tag": a.tag,
            "date": a.date or str(a.created_at)[:10],
        }
        for a in announcements
    ]
    return success(data, "获取成功")
