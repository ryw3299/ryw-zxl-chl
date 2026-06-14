"""学习路径服务。"""

from sqlalchemy.orm import Session

from src.models.learning_path import LearningPath
from src.models.profile import StudentProfile
from src.services.dify_service import generate_path as ai_generate_path


class PathNotFound(Exception):
    pass


async def generate_path(
    db: Session,
    user_id: int,
    profile_id: int,
    daily_hours: float = 2.0,
    learning_cycle_days: int = 30,
    goal: str = "",
) -> dict:
    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id).first()
    if not profile:
        raise PathNotFound("画像不存在")

    preferences = {
        "daily_hours": daily_hours,
        "learning_cycle_days": learning_cycle_days,
        "goal": goal,
    }
    result = await ai_generate_path(profile.profile_json, preferences)

    path = LearningPath(
        user_id=user_id,
        profile_id=profile_id,
        title=result.get("path_title", "个性化学习路径"),
        natural_language_summary=result.get("natural_language_summary", ""),
        path_json=result,
        status="active",
    )
    db.add(path)
    db.commit()
    db.refresh(path)

    return _format_path(path)


def get_path_list(db: Session, user_id: int) -> list[dict]:
    paths = (
        db.query(LearningPath)
        .filter(LearningPath.user_id == user_id)
        .order_by(LearningPath.created_at.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "title": p.title,
            "status": p.status,
            "created_at": str(p.created_at),
        }
        for p in paths
    ]


def get_path_detail(db: Session, path_id: int, user_id: int) -> dict:
    path = db.query(LearningPath).filter(
        LearningPath.id == path_id, LearningPath.user_id == user_id
    ).first()
    if not path:
        raise PathNotFound("学习路径不存在")
    return _format_path(path)


def update_path_status(db: Session, path_id: int, user_id: int, status: str) -> dict:
    path = db.query(LearningPath).filter(
        LearningPath.id == path_id, LearningPath.user_id == user_id
    ).first()
    if not path:
        raise PathNotFound("学习路径不存在")
    path.status = status
    db.commit()
    db.refresh(path)
    return _format_path(path)


def _format_path(p: LearningPath) -> dict:
    return {
        "id": p.id,
        "title": p.title,
        "natural_language_summary": p.natural_language_summary,
        "path_json": p.path_json,
        "status": p.status,
        "created_at": str(p.created_at),
        "updated_at": str(p.updated_at),
    }
