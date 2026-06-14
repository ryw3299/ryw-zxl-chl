"""学习记录路由。"""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.deps import get_current_user
from src.models.supplement import StudyRecord
from src.models.user import User
from src.utils.response import success

router = APIRouter(prefix="/study-records", tags=["学习记录"])


@router.get("", summary="获取学习记录")
def list_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    records = (
        db.query(StudyRecord)
        .filter(StudyRecord.user_id == current_user.id)
        .order_by(StudyRecord.study_date.desc())
        .limit(20)
        .all()
    )
    data = [
        {
            "id": r.id,
            "resource_title": r.resource_title,
            "study_date": r.study_date,
            "duration_minutes": r.duration_minutes,
            "record_type": r.record_type,
            "progress_percent": r.progress_percent,
            "chapter": r.chapter,
        }
        for r in records
    ]
    return success(data, "获取成功")


@router.get("/stats", summary="获取学习统计")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    today = datetime.now().strftime("%Y-%m-%d")
    records = db.query(StudyRecord).filter(StudyRecord.user_id == current_user.id).all()

    total_minutes = sum(r.duration_minutes or 0 for r in records)
    today_minutes = sum(r.duration_minutes or 0 for r in records if r.study_date == today)
    total_days = len(set(r.study_date for r in records))
    streak = 0

    # Simple streak: count consecutive days backwards from today
    from datetime import timedelta
    check_date = datetime.now()
    for _ in range(365):
        day_str = check_date.strftime("%Y-%m-%d")
        if any(r.study_date == day_str for r in records):
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break

    return success({
        "total_hours": round(total_minutes / 60, 1),
        "today_minutes": today_minutes,
        "total_days": total_days,
        "streak_days": streak,
        "total_minutes": total_minutes,
    }, "获取成功")
