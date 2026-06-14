"""画像服务。"""

from datetime import datetime

from sqlalchemy.orm import Session

from src.models.profile import StudentProfile
from src.services.dify_service import generate_profile as ai_generate_profile


class ProfileNotFound(Exception):
    pass


async def init_profile(db: Session, user_id: int, chat_history: list[dict]) -> dict:
    """初始化画像：调用 Dify 生成画像并保存。"""
    result = await ai_generate_profile(chat_history)

    profile = StudentProfile(
        user_id=user_id,
        profile_json=result,
        summary=result.get("summary", ""),
        version=1,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return _format_profile(profile)


def get_latest_profile(db: Session, user_id: int) -> dict:
    profile = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == user_id)
        .order_by(StudentProfile.version.desc())
        .first()
    )
    if not profile:
        raise ProfileNotFound("尚未生成学生画像")
    return _format_profile(profile)


def get_profile_history(db: Session, user_id: int) -> list[dict]:
    profiles = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == user_id)
        .order_by(StudentProfile.version.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "summary": p.summary,
            "version": p.version,
            "created_at": str(p.created_at),
        }
        for p in profiles
    ]


def _format_profile(p: StudentProfile) -> dict:
    return {
        "id": p.id,
        "profile_json": p.profile_json,
        "summary": p.summary,
        "version": p.version,
        "created_at": str(p.created_at),
        "updated_at": str(p.updated_at),
    }
