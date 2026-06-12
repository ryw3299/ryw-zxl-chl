"""Assemble a ``StudentTurnContext`` by orchestrating backend services.

This is the single function that ``qa_service`` calls before handing off
to the student agent.  It replaces the previous pattern where structured
content was passed into every tool.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session as DBSession

from src.api.models.tables import Lesson, Script
from src.schemas.common import StructuredLessonContent
from src.schemas.generate_schemas import LessonScript
from src.schemas.student_turn_context import StudentTurnContext
from src.utils.student.question_classifier import classify_question_type, is_chitchat

from .conversation_service import ConversationService
from .retrieval_service import RetrievalService
from .session_service import SessionService

logger = logging.getLogger(__name__)


def build_turn_context(
    db: DBSession,
    *,
    lesson_id: str,
    session_id: str,
    user_id: str,
    school_id: Optional[str] = None,
    course_id: str,
    question: str,
    current_section_id: Optional[str] = None,
    current_page: Optional[int] = None,
    current_script_block_id: Optional[str] = None,
    history_qa: Optional[list[dict[str, Any]]] = None,
) -> Optional[StudentTurnContext]:
    """Build a complete turn context by running all pre-agent steps.

    Returns ``None`` when the lesson has no structured content yet (the
    caller should fall back to a generic error response).
    """

    # 1. Load lesson content from MySQL
    structured_content, lesson_script = _load_lesson_content(db, lesson_id)
    if structured_content is None:
        return None

    # 2. Session
    session_snapshot = SessionService.get_or_init(
        db,
        session_id=session_id,
        user_id=user_id,
        school_id=school_id,
        course_id=course_id,
        lesson_id=lesson_id,
    )

    # Merge position hints (API params take priority over DB state)
    effective_section_id = current_section_id or session_snapshot.current_section_id
    effective_page = current_page if current_page is not None else session_snapshot.current_page
    effective_script_block_id = current_script_block_id or session_snapshot.current_script_block_id

    # 3. Conversation history
    conv_service = ConversationService()
    recent_turns = conv_service.load_recent_turns(
        session_id,
        limit=5,
        fallback_history_qa=history_qa,
    )

    # 4. Question classification (done early so we can skip retrieval for chitchat)
    question_type = classify_question_type(question)

    # 5. Retrieval (pre-RAG) -- skip for chitchat / greetings
    from src.services.student.retrieval_service import RetrievalResult

    if question_type == "chitchat" or is_chitchat(question):
        retrieval_result = RetrievalResult()
    else:
        kb_index_path = _get_kb_index_path(db, lesson_id)
        retrieval_result = RetrievalService.do_retrieval(
            lesson_id=lesson_id,
            question=question,
            structured_content=structured_content,
            lesson_script=lesson_script,
            prefer_section_id=effective_section_id,
            prefer_page=effective_page,
            prefer_script_block_id=effective_script_block_id,
            kb_index_path=kb_index_path,
        )

    return StudentTurnContext(
        session_id=session_id,
        user_id=user_id,
        course_id=course_id,
        lesson_id=lesson_id,
        question=question,
        question_type=question_type,
        current_section_id=effective_section_id,
        current_page=effective_page,
        current_script_block_id=effective_script_block_id,
        session_snapshot=session_snapshot,
        recent_turns=recent_turns,
        retrieved_chunks=retrieval_result.chunks,
        exact_source=retrieval_result.exact_source,
        structured_content=structured_content,
        lesson_script=lesson_script,
    )


def _get_kb_index_path(db: DBSession, lesson_id: str) -> Optional[str]:
    """Look up the KB index path for a lesson (returns None if not linked)."""
    try:
        lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
        if lesson is None or not getattr(lesson, "knowledge_base_id", None):
            return None
        from src.api.models.tables import KnowledgeBase

        kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == lesson.knowledge_base_id).first()
        if kb is None or kb.status != "ready" or not kb.index_path:
            return None
        return kb.index_path
    except Exception:
        return None


def _load_lesson_content(
    db: DBSession,
    lesson_id: str,
) -> tuple[Optional[StructuredLessonContent], Optional[LessonScript]]:
    """Load structured content and lesson script from MySQL."""
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None:
        return None, None

    sc_dict = None
    if lesson.structured_content:
        sc_dict = json.loads(lesson.structured_content)
        if isinstance(sc_dict, dict):
            sc_dict = _normalize_structured_content_dict(sc_dict, lesson=lesson)

    if (not _has_teaching_context(sc_dict)) and lesson.slide_plan_json:
        try:
            sc_dict = _structured_content_from_slide_plan(
                json.loads(lesson.slide_plan_json),
                lesson=lesson,
            )
        except Exception:
            logger.debug("Failed to synthesize structured_content from slide_plan for %s", lesson_id, exc_info=True)

    if not _has_teaching_context(sc_dict):
        return None, None

    structured_content = StructuredLessonContent.model_validate(sc_dict)

    lesson_script: Optional[LessonScript] = None
    if lesson.script_id:
        script = db.query(Script).filter(Script.script_id == lesson.script_id).first()
        if script and script.generate_output:
            gen_output = json.loads(script.generate_output)
            ls_dict = gen_output.get("lesson_script")
            if ls_dict:
                lesson_script = LessonScript.model_validate(ls_dict)

    return structured_content, lesson_script


def _has_teaching_context(sc_dict: Any) -> bool:
    if not isinstance(sc_dict, dict):
        return False
    return bool(sc_dict.get("pages") or sc_dict.get("sections") or sc_dict.get("knowledge_points"))


def _normalize_structured_content_dict(sc_dict: dict, *, lesson: Lesson) -> dict:
    sc_dict = dict(sc_dict)
    sc_dict["lesson_id"] = sc_dict.get("lesson_id") or lesson.lesson_id
    if lesson.course_id and not sc_dict.get("course_id"):
        sc_dict["course_id"] = lesson.course_id

    for index, page in enumerate(sc_dict.get("pages") or [], start=1):
        if isinstance(page, dict):
            page["lesson_id"] = page.get("lesson_id") or lesson.lesson_id
            if lesson.course_id and not page.get("course_id"):
                page["course_id"] = lesson.course_id
            page["page"] = int(page.get("page") or page.get("page_number") or index)

    for index, section in enumerate(sc_dict.get("sections") or [], start=1):
        if isinstance(section, dict):
            section["lesson_id"] = section.get("lesson_id") or lesson.lesson_id
            if lesson.course_id and not section.get("course_id"):
                section["course_id"] = lesson.course_id
            section["section_id"] = section.get("section_id") or section.get("sectionId") or f"section-{index}"
            section["name"] = section.get("name") or section.get("title") or f"Page {index}"

    sc_dict.setdefault("source_asset_ids", [])
    sc_dict.setdefault("lesson_summary", "")
    sc_dict.setdefault("knowledge_points", [])
    return sc_dict


def _slide_points(slide: dict) -> list[str]:
    raw_points = (
        slide.get("key_points")
        or slide.get("keyPoints")
        or slide.get("bullets")
        or slide.get("points")
        or slide.get("objectives")
        or []
    )
    points: list[str] = []
    if isinstance(raw_points, list):
        for item in raw_points:
            if isinstance(item, str) and item.strip():
                points.append(item.strip())
            elif isinstance(item, dict):
                text = item.get("text") or item.get("title") or item.get("content") or item.get("point")
                if text:
                    points.append(str(text).strip())
    return points


def _structured_content_from_slide_plan(slide_plan: dict, *, lesson: Lesson) -> Optional[dict]:
    slides = slide_plan.get("slides") if isinstance(slide_plan, dict) else None
    if not isinstance(slides, list) or not slides:
        return None

    pages = []
    sections = []
    all_points: list[str] = []

    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            continue
        page_number = int(slide.get("page") or slide.get("page_number") or slide.get("pageNumber") or index)
        section_id = slide.get("section_id") or slide.get("sectionId") or slide.get("id") or f"slide-{page_number}"
        title = slide.get("title") or slide.get("heading") or slide.get("name") or f"Page {page_number}"
        summary = (
            slide.get("summary")
            or slide.get("description")
            or slide.get("subtitle")
            or slide.get("teaching_goal")
            or slide.get("teachingGoal")
            or ""
        )
        points = _slide_points(slide)
        all_points.extend(points)
        content = "\n".join([str(summary or "").strip(), *points]).strip()

        pages.append(
            {
                "page_id": f"page-{page_number}",
                "course_id": lesson.course_id,
                "lesson_id": lesson.lesson_id,
                "section_id": section_id,
                "page": page_number,
                "title": title,
                "content": content or title,
                "summary": summary,
                "key_points": points,
                "knowledge_points": points,
                "source_unit_ids": [],
                "page_role": "other",
            }
        )
        sections.append(
            {
                "section_id": section_id,
                "course_id": lesson.course_id,
                "lesson_id": lesson.lesson_id,
                "name": title,
                "summary": summary,
                "page_range": [page_number],
                "key_points": points,
                "knowledge_points": points,
                "source_unit_ids": [],
                "section_type": "other",
            }
        )

    if not pages:
        return None

    return {
        "course_id": lesson.course_id,
        "lesson_id": lesson.lesson_id,
        "source_asset_ids": [],
        "lesson_summary": slide_plan.get("deck_title") or lesson.lesson_name or "",
        "pages": pages,
        "sections": sections,
        "knowledge_points": list(dict.fromkeys([point for point in all_points if point])),
        "metadata": {"source": "slide_plan"},
    }
