"""画像服务。"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models.profile import StudentProfile
from src.models.profile_generation import ProfileGenerationRecord
from src.services.dify_service import generate_profile as ai_generate_profile


class ProfileNotFound(Exception):
    pass


async def init_profile(
    db: Session, user_id: int, chat_history: list[dict], conversation_id: str = ""
) -> dict:
    """初始化画像：调用 Dify Chatflow 生成画像并保存完整结果。"""
    result = await ai_generate_profile(chat_history, user_id, conversation_id)
    payload = result["profile_payload"]
    profile_ready = bool(payload.get("profile_ready"))
    student_profile = payload.get("student_profile") or {}
    summary = payload.get("profile_summary") or student_profile.get("summary", "")
    profile = None

    if profile_ready and student_profile:
        version = (
            db.query(func.max(StudentProfile.version))
            .filter(StudentProfile.user_id == user_id)
            .scalar()
            or 0
        ) + 1
        profile = StudentProfile(
            user_id=user_id,
            profile_json=student_profile,
            summary=summary,
            version=version,
        )
        db.add(profile)
        db.flush()

    record = ProfileGenerationRecord(
        user_id=user_id,
        profile_id=profile.id if profile else None,
        request_json={
            "chat_history": chat_history,
            "conversation_id": conversation_id,
            "request_payload": result.get("request_payload", {}),
        },
        response_json={
            "provider": result.get("provider", ""),
            "http_response": result.get("http_response", {}),
            "profile_payload": payload,
        },
        conversation_id=result.get("conversation_id", ""),
        message_id=result.get("message_id", ""),
        profile_ready=profile_ready,
        profile_type=payload.get("profile_type", ""),
        profile_summary=summary,
        dialogue_summary=payload.get("dialogue_summary", ""),
        frontend_message=payload.get("frontend_message", ""),
    )
    db.add(record)
    db.flush()
    _prune_generation_records(db, user_id)
    db.commit()
    db.refresh(record)

    if profile:
        db.refresh(profile)

    return _format_init_result(profile, record, payload, result)


def _prune_generation_records(db: Session, user_id: int, keep_latest: int = 5) -> None:
    old_records = (
        db.query(ProfileGenerationRecord)
        .filter(ProfileGenerationRecord.user_id == user_id)
        .order_by(
            ProfileGenerationRecord.created_at.desc(),
            ProfileGenerationRecord.id.desc(),
        )
        .offset(keep_latest)
        .all()
    )
    for old_record in old_records:
        db.delete(old_record)


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


def get_latest_init_state(db: Session, user_id: int) -> dict:
    record = (
        db.query(ProfileGenerationRecord)
        .filter(ProfileGenerationRecord.user_id == user_id)
        .order_by(ProfileGenerationRecord.created_at.desc(), ProfileGenerationRecord.id.desc())
        .first()
    )
    if not record or record.profile_ready:
        return {
            "has_draft": False,
            "conversation_id": "",
            "generation_record_id": None,
            "messages": [],
            "updated_at": "",
        }

    request_json = record.request_json or {}
    raw_messages = request_json.get("chat_history") or []
    messages: list[dict] = []
    for item in raw_messages:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "")).strip()
        content = str(item.get("content", "")).strip()
        if role and content:
            messages.append({"role": role, "content": content})

    latest_assistant_message = (record.frontend_message or "").strip()
    if latest_assistant_message and (
        not messages
        or messages[-1].get("role") != "assistant"
        or messages[-1].get("content") != latest_assistant_message
    ):
        messages.append({"role": "assistant", "content": latest_assistant_message})

    return {
        "has_draft": bool(messages),
        "conversation_id": record.conversation_id or request_json.get("conversation_id", ""),
        "generation_record_id": record.id,
        "messages": messages,
        "updated_at": str(record.created_at),
    }


def _format_profile(p: StudentProfile) -> dict:
    return {
        "id": p.id,
        "profile_json": p.profile_json,
        "summary": p.summary,
        "version": p.version,
        "created_at": str(p.created_at),
        "updated_at": str(p.updated_at),
    }


def _format_init_result(
    profile: StudentProfile | None,
    record: ProfileGenerationRecord,
    payload: dict,
    result: dict,
) -> dict:
    student_profile = payload.get("student_profile") if payload.get("profile_ready") else None
    summary = payload.get("profile_summary") or (student_profile or {}).get("summary", "")
    return {
        "id": profile.id if profile else None,
        "profile_json": profile.profile_json if profile else student_profile,
        "student_profile": student_profile,
        "summary": summary,
        "profile_summary": summary,
        "version": profile.version if profile else 0,
        "created_at": str(profile.created_at) if profile else "",
        "updated_at": str(profile.updated_at) if profile else "",
        "profile_ready": bool(payload.get("profile_ready")),
        "profile_type": payload.get("profile_type", ""),
        "dialogue_summary": payload.get("dialogue_summary", ""),
        "collected_info": payload.get("collected_info", {}),
        "frontend_message": payload.get("frontend_message", ""),
        "conversation_id": result.get("conversation_id", ""),
        "message_id": result.get("message_id", ""),
        "generation_record_id": record.id,
        "missing_information": (
            (student_profile or {}).get("missing_information", [])
            if isinstance(student_profile, dict)
            else []
        ),
    }
