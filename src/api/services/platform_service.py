"""Service layer for external platform integration (course / user sync)."""

import json
import secrets

from sqlalchemy.orm import Session

from src.api.deps import generate_id
from src.api.models.tables import Course, User


def sync_course(db: Session, *, platform_id: str, course_info: dict) -> dict:
    """Idempotently upsert a course pulled from the external platform."""
    platform_course_id = course_info.get("courseId", "")

    existing = (
        db.query(Course)
        .filter(
            Course.platform_id == platform_id,
            Course.platform_course_id == platform_course_id,
        )
        .first()
    )

    if existing:
        existing.course_name = course_info.get("courseName", existing.course_name)
        existing.school_name = course_info.get("schoolName", existing.school_name)
        existing.teacher_info = json.dumps(course_info.get("teacherInfo", []), ensure_ascii=False)
        existing.term = course_info.get("term", existing.term)
        existing.credit = course_info.get("credit", existing.credit)
        existing.period = course_info.get("period", existing.period)
        existing.course_cover = course_info.get("courseCover", existing.course_cover)
        db.commit()
        db.refresh(existing)
        return {
            "internalCourseId": existing.course_id,
            "syncStatus": "success",
        }

    internal_id = generate_id("cou")
    course = Course(
        course_id=internal_id,
        platform_course_id=platform_course_id,
        platform_id=platform_id,
        course_name=course_info.get("courseName", ""),
        school_id=course_info.get("schoolId"),
        school_name=course_info.get("schoolName"),
        teacher_info=json.dumps(course_info.get("teacherInfo", []), ensure_ascii=False),
        term=course_info.get("term"),
        credit=course_info.get("credit"),
        period=course_info.get("period"),
        course_cover=course_info.get("courseCover"),
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return {
        "internalCourseId": course.course_id,
        "syncStatus": "success",
    }


def sync_user(db: Session, *, platform_id: str, user_info: dict) -> dict:
    """Idempotently upsert a user pulled from the external platform."""
    platform_user_id = user_info.get("userId", "")

    existing = (
        db.query(User)
        .filter(
            User.platform_id == platform_id,
            User.platform_user_id == platform_user_id,
        )
        .first()
    )

    if existing:
        existing.user_name = user_info.get("userName", existing.user_name)
        existing.role = user_info.get("role", existing.role)
        existing.email = user_info.get("contactInfo", {}).get("email", existing.email)
        existing.phone = user_info.get("contactInfo", {}).get("phone", existing.phone)
        existing.related_course_ids = json.dumps(user_info.get("relatedCourseIds", []), ensure_ascii=False)
        db.commit()
        db.refresh(existing)
        return {
            "internalUserId": existing.user_id,
            "syncStatus": "success",
            "authToken": existing.auth_token or "",
        }

    internal_id = generate_id("usr")
    auth_token = secrets.token_urlsafe(64)
    user = User(
        user_id=internal_id,
        platform_user_id=platform_user_id,
        platform_id=platform_id,
        user_name=user_info.get("userName", ""),
        role=user_info.get("role", "student"),
        school_id=user_info.get("schoolId"),
        email=user_info.get("contactInfo", {}).get("email"),
        phone=user_info.get("contactInfo", {}).get("phone"),
        auth_token=auth_token,
        related_course_ids=json.dumps(user_info.get("relatedCourseIds", []), ensure_ascii=False),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {
        "internalUserId": user.user_id,
        "syncStatus": "success",
        "authToken": auth_token,
    }
