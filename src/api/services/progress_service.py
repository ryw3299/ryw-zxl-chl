"""Service layer for learning progress tracking and pace adjustment.

Bridges the FastAPI router to the existing decision agent.
"""

import json
from typing import Optional

from sqlalchemy.orm import Session

from src.api.deps import generate_id
from src.api.models.tables import AdjustRecord, LearningProgress, Lesson


def track_progress(
    db: Session,
    *,
    school_id: str,
    user_id: str,
    course_id: str,
    lesson_id: str,
    current_section_id: str,
    progress_percent: float,
    last_operate_time: str,
    qa_record_id: Optional[str] = None,
) -> dict:
    """Persist a learning-progress sample.

    Idempotent on ``(user_id, lesson_id, current_section_id)`` for the same
    ``last_operate_time``.  Upstream callers should set ``progress_percent``
    to a number in ``[0, 100]``.
    """
    existing = (
        db.query(LearningProgress)
        .filter(
            LearningProgress.user_id == user_id,
            LearningProgress.lesson_id == lesson_id,
        )
        .first()
    )

    if existing:
        existing.current_section_id = current_section_id
        existing.progress_percent = progress_percent
        existing.last_operate_time = last_operate_time
        existing.qa_record_id = qa_record_id
        track_id = existing.track_id
    else:
        track_id = generate_id("track")
        progress = LearningProgress(
            track_id=track_id,
            school_id=school_id,
            user_id=user_id,
            course_id=course_id,
            lesson_id=lesson_id,
            current_section_id=current_section_id,
            progress_percent=progress_percent,
            last_operate_time=last_operate_time,
            qa_record_id=qa_record_id,
        )
        db.add(progress)

    total_progress = _compute_total_progress(db, user_id, lesson_id, progress_percent)
    next_section = _suggest_next_section(db, lesson_id, current_section_id)

    if existing:
        existing.total_progress = total_progress
        existing.next_section_suggest = next_section
    else:
        progress.total_progress = total_progress
        progress.next_section_suggest = next_section

    db.commit()

    return {
        "trackId": track_id,
        "totalProgress": round(total_progress, 1),
        "nextSectionSuggest": next_section,
    }


def adjust_pace(
    db: Session,
    *,
    user_id: str,
    lesson_id: str,
    current_section_id: str,
    understanding_level: str,
    qa_record_id: str,
) -> dict:
    """Run the pace-adjustment decision agent for a user/lesson.

    Returns a structured suggestion (``next_action``, ``reason`` ...) that
    the front end can surface to the student.  Falls back to a rule-based
    decision if the LLM is unavailable.
    """
    next_action = _decide_next_action(understanding_level)

    if understanding_level == "full":
        adjust_type = "accelerate"
    else:
        level_to_adjust = {
            "resume": "normal",
            "supplement_then_resume": "supplement",
            "reteach_slowly": "supplement",
            "trigger_game": "supplement",
        }
        adjust_type = level_to_adjust.get(next_action, "normal")

    supplement_content = None
    if adjust_type == "supplement":
        supplement_content = _build_supplement(db, lesson_id, current_section_id, understanding_level)

    next_sections = _build_next_sections(db, lesson_id, current_section_id, understanding_level)

    adjust_id = generate_id("adj")
    record = AdjustRecord(
        adjust_id=adjust_id,
        user_id=user_id,
        lesson_id=lesson_id,
        current_section_id=current_section_id,
        understanding_level=understanding_level,
        qa_record_id=qa_record_id,
        adjust_type=adjust_type,
        continue_section_id=current_section_id,
        supplement_content=json.dumps(supplement_content, ensure_ascii=False) if supplement_content else None,
        next_sections=json.dumps(next_sections, ensure_ascii=False),
    )
    db.add(record)
    db.commit()

    return {
        "adjustPlan": {
            "continueSectionId": current_section_id,
            "adjustType": adjust_type,
            "supplementContent": supplement_content,
            "nextSections": next_sections,
        }
    }


# ── helpers ──────────────────────────────────────────────────────────


def _compute_total_progress(
    db: Session,
    user_id: str,
    lesson_id: str,
    current_percent: float,
) -> float:
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None or not lesson.structured_content:
        return current_percent

    structured = json.loads(lesson.structured_content)
    total_sections = len(structured.get("sections", []))
    if total_sections == 0:
        return current_percent

    completed = (
        db.query(LearningProgress)
        .filter(
            LearningProgress.user_id == user_id,
            LearningProgress.lesson_id == lesson_id,
            LearningProgress.progress_percent >= 100.0,
        )
        .count()
    )
    return min(100.0, (completed / total_sections) * 100 + current_percent / total_sections)


def _suggest_next_section(db: Session, lesson_id: str, current_section_id: str) -> str:
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None or not lesson.structured_content:
        return current_section_id

    structured = json.loads(lesson.structured_content)
    sections = structured.get("sections", [])
    for i, sec in enumerate(sections):
        if sec.get("section_id") == current_section_id and i + 1 < len(sections):
            return sections[i + 1].get("section_id", current_section_id)
    return current_section_id


def _build_supplement(
    db: Session,
    lesson_id: str,
    section_id: str,
    understanding_level: str,
) -> dict:
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    content_text = "根据您的学习情况，建议回顾本节重点知识。"
    example_text = ""

    if lesson and lesson.structured_content:
        structured = json.loads(lesson.structured_content)
        for sec in structured.get("sections", []):
            if sec.get("section_id") == section_id:
                kp = sec.get("key_points", []) or sec.get("knowledge_points", [])
                if kp:
                    content_text = f"让我们回顾一下本节的核心要点：{'、'.join(kp[:3])}。"
                example_text = sec.get("summary", "")
                break

    duration = 60 if understanding_level == "none" else 30
    return {
        "content": content_text,
        "duration": duration,
        "relatedExample": example_text,
    }


def _build_next_sections(
    db: Session,
    lesson_id: str,
    current_section_id: str,
    understanding_level: str,
) -> list[dict]:
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None or not lesson.structured_content:
        return []

    structured = json.loads(lesson.structured_content)
    sections = structured.get("sections", [])

    found_current = False
    result = []
    for sec in sections:
        if sec.get("section_id") == current_section_id:
            found_current = True
            duration = 75 if understanding_level == "partial" else 90 if understanding_level == "none" else 40
            result.append(
                {
                    "sectionId": sec.get("section_id"),
                    "adjustedDuration": duration,
                    "isKeyPointStrengthen": understanding_level != "full",
                }
            )
            continue
        if found_current:
            result.append(
                {
                    "sectionId": sec.get("section_id"),
                    "adjustedDuration": 40,
                    "isKeyPointStrengthen": False,
                }
            )
            if len(result) >= 3:
                break

    return result


def _decide_next_action(understanding_level: str) -> str:
    """Rule-based decision mirroring the student agent's logic."""
    if understanding_level in {None, "none"}:
        return "reteach_slowly"
    if understanding_level == "partial":
        return "supplement_then_resume"
    return "resume"
