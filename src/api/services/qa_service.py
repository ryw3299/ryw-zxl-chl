"""Service layer for Q&A interaction.

Bridges the FastAPI router to the StudentOpenHandsAgent.
Uses the new backend-orchestrated pipeline:
  1. build_turn_context()  -- session + history + RAG
  2. run_student_agent()   -- agent only does answer + decision + optional game
  3. persist results
"""

import json
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from src.api.deps import generate_id
from src.api.models.tables import Lesson, QARecord, QASession

logger = logging.getLogger(__name__)


def get_or_create_session(
    db: Session,
    *,
    session_id: str,
    user_id: str,
    school_id: str,
    course_id: str,
    lesson_id: str,
) -> QASession:
    """Idempotently fetch or create a ``QASession`` row.

    The row is keyed by ``session_id``.  When inserting, we copy the four
    auxiliary identifiers (school/user/course/lesson) so future queries
    can filter by any of them without an extra join.

    Args:
        db: Active SQLAlchemy session, committed/refreshed on insert.
        session_id: Stable client-supplied session identifier.
        user_id: Owner of the session.
        school_id: Tenant identifier for the platform integration.
        course_id: Course the session belongs to.
        lesson_id: Lesson currently being studied.

    Returns:
        The persisted ``QASession`` row, either freshly created or
        reused from the database.
    """
    session = db.query(QASession).filter(QASession.session_id == session_id).first()
    if session is None:
        session = QASession(
            session_id=session_id,
            user_id=user_id,
            school_id=school_id,
            course_id=course_id,
            lesson_id=lesson_id,
            status="active",
        )
        db.add(session)
        db.commit()
        db.refresh(session)
    return session


def run_qa_interact(
    db: Session,
    *,
    session: QASession,
    user_id: str,
    question_type: str,
    question_content: str,
    current_section_id: Optional[str] = None,
    current_page: Optional[int] = None,
    current_script_block_id: Optional[str] = None,
    history_qa: Optional[list[dict]] = None,
) -> dict:
    """Drive one full Q&A interaction turn.

    The pipeline is::

        build_turn_context()  -> session + RAG + history (sync, in DB)
        run_student_agent()    -> answer + decision (+ optional game)
        persist QARecord       -> update session position
        return camelCase dict  -> shaped for ``QAInteractData``

    On any unexpected failure (missing dependencies, lesson not parsed,
    unhandled agent exception) a friendly fallback is returned with
    ``code=200`` so the front end never sees a 500.

    Args:
        db: Active SQLAlchemy session.
        session: Already-loaded :class:`QASession` row for the user.
        user_id: Owner of the request (used for ``QARecord.user_id``).
        question_type: Either ``"text"`` or ``"voice"``.
        question_content: The user's literal question text.
        current_section_id: Optional cursor in the lesson outline.
        current_page: Optional page number cursor.
        current_script_block_id: Optional script block cursor.
        history_qa: Optional list of prior turns supplied by the caller.

    Returns:
        A camelCase dict matching ``QAInteractData`` keys.
    """
    try:
        from src.agents import run_student_agent
    except ImportError as exc:
        logger.warning("Student agent unavailable (missing dependency: %s), using fallback", exc)
        return _build_fallback_response(
            question_content,
            error=(
                "学生 Agent 依赖未安装（请按当前选定的 STUDENT_AGENT_BACKEND 安装："
                "claude → claude_agent_sdk；openhands → openhands）"
            ),
        )

    # ------------------------------------------------------------------
    # NEW PATH: build TurnContext via backend services, then call agent
    # ------------------------------------------------------------------
    try:
        from src.services.student.context_builder import build_turn_context

        turn_context = build_turn_context(
            db,
            lesson_id=session.lesson_id,
            session_id=session.session_id,
            user_id=user_id,
            school_id=getattr(session, "school_id", None),
            course_id=session.course_id,
            question=question_content,
            current_section_id=current_section_id,
            current_page=current_page,
            current_script_block_id=current_script_block_id,
            history_qa=history_qa,
        )

        if turn_context is None:
            return _build_fallback_response(question_content)

        agent_request = {
            "course_id": session.course_id,
            "lesson_id": session.lesson_id,
            "session_id": session.session_id,
            "question": question_content,
            "turn_context": turn_context.model_dump(mode="python"),
            "current_section_id": current_section_id,
            "current_page": current_page,
            "current_script_block_id": current_script_block_id,
            "history_qa": _build_qa_history(history_qa),
        }

    except Exception:
        logger.debug("context_builder unavailable, falling back to legacy path", exc_info=True)
        agent_request = _build_legacy_agent_request(
            db,
            session=session,
            question_content=question_content,
            current_section_id=current_section_id,
            current_page=current_page,
            current_script_block_id=current_script_block_id,
            history_qa=history_qa,
        )
        if agent_request is None:
            return _build_fallback_response(question_content)

    try:
        llm = _get_agent_llm()
        agent_result = run_student_agent(agent_request, llm=llm)
    except Exception as exc:
        logger.exception("Student agent failed for session %s", session.session_id)
        return _build_fallback_response(
            question_content,
            error=f"AI 服务暂时不可用（{str(exc)[:60]}），请稍后重试或联系管理员",
        )

    # ------------------------------------------------------------------
    # Post-processing: persist and build response
    #
    # Both backends (OpenHands & Claude) return ``StudentAgentResponse``
    # dumped to dict via ``run_student_agent``.  We read the standardized
    # response fields rather than legacy intermediate keys.
    # ------------------------------------------------------------------
    response_payload = _normalize_agent_result(agent_result)

    answer_content = response_payload.get("answer", "")
    understanding_level = response_payload.get("understanding_level") or "none"
    next_action = response_payload.get("next_action")
    reason = response_payload.get("reason", "")
    agent_question_type = response_payload.get("question_type", "unknown")
    suggested_questions = response_payload.get("suggested_questions", []) or []
    matched_section_id = response_payload.get("matched_section_id")
    matched_page = response_payload.get("matched_page")
    target_section_id = response_payload.get("target_section_id")
    target_page = response_payload.get("target_page")
    recommended_narration_level = response_payload.get("recommended_narration_level")
    references = response_payload.get("references", []) or []

    related_knowledge = _extract_related_knowledge(response_payload, current_section_id)

    answer_id = generate_id("ans")
    record = QARecord(
        answer_id=answer_id,
        session_id=session.session_id,
        user_id=user_id,
        course_id=session.course_id,
        lesson_id=session.lesson_id,
        question_type=question_type,
        question_content=question_content,
        current_section_id=current_section_id,
        answer_content=answer_content,
        answer_type="text",
        related_knowledge=json.dumps(related_knowledge, ensure_ascii=False) if related_knowledge else None,
        suggestions=json.dumps(suggested_questions, ensure_ascii=False),
        understanding_level=understanding_level,
        next_action=next_action,
        reason=reason,
        matched_section_id=matched_section_id,
        matched_page=matched_page,
        target_section_id=target_section_id,
        target_page=target_page,
        references_json=json.dumps(references, ensure_ascii=False, default=str) if references else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    # Update session position if the new columns exist
    try:
        from src.services.student.session_service import SessionService

        SessionService.update_position(
            db,
            session.session_id,
            current_section_id=target_section_id or matched_section_id,
            current_page=target_page or matched_page,
            last_action=next_action,
        )
    except Exception:  # noqa: BLE001 - session update is best-effort.
        logger.debug(
            "SessionService.update_position failed for session %s",
            session.session_id,
            exc_info=True,
        )

    return {
        "answerId": record.answer_id,
        "answerContent": answer_content,
        "answerType": "text",
        "relatedKnowledge": related_knowledge,
        "suggestions": suggested_questions,
        "understandingLevel": understanding_level,
        "questionType": agent_question_type,
        "recommendedNarrationLevel": recommended_narration_level,
        "nextAction": next_action,
        "reason": reason,
        "matchedSectionId": matched_section_id,
        "matchedPage": matched_page,
        "targetSectionId": target_section_id,
        "targetPage": target_page,
    }


def _voice_to_text_placeholder(voice_url: str, language: str = "zh-CN") -> dict:
    """Placeholder for ASR integration."""
    return {
        "text": "[语音识别结果占位 - 需接入ASR服务]",
        "confidence": 0.0,
    }


# ── helpers ──────────────────────────────────────────────────────────


def _build_legacy_agent_request(
    db: Session,
    *,
    session: QASession,
    question_content: str,
    current_section_id: Optional[str],
    current_page: Optional[int],
    current_script_block_id: Optional[str],
    history_qa: Optional[list[dict]],
) -> Optional[dict]:
    """Build agent request dict the old way (with structured_content)."""
    structured_content, lesson_script = _load_lesson_content(db, session.lesson_id)
    if structured_content is None:
        return None

    return {
        "course_id": session.course_id,
        "lesson_id": session.lesson_id,
        "session_id": session.session_id,
        "question": question_content,
        "structured_content": structured_content,
        "lesson_script": lesson_script,
        "current_section_id": current_section_id,
        "current_page": current_page,
        "current_script_block_id": current_script_block_id,
        "history_qa": _build_qa_history(history_qa),
    }


def _load_lesson_content(db: Session, lesson_id: str) -> tuple[Optional[dict], Optional[dict]]:
    """Load structured_content and lesson_script from the Lesson + Script tables."""
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None:
        return None, None

    structured_content = None
    if lesson.structured_content:
        structured_content = json.loads(lesson.structured_content)
        if isinstance(structured_content, dict):
            structured_content = _normalize_structured_content_payload(
                structured_content,
                lesson_id=lesson.lesson_id,
                course_id=lesson.course_id,
            )

    if (not _has_teaching_context(structured_content)) and lesson.slide_plan_json:
        try:
            structured_content = _structured_content_from_slide_plan(
                json.loads(lesson.slide_plan_json),
                lesson_id=lesson.lesson_id,
                course_id=lesson.course_id,
                lesson_name=lesson.lesson_name,
            )
        except Exception:
            logger.debug("Failed to build structured_content from slide_plan for lesson %s", lesson_id, exc_info=True)

    if not _has_teaching_context(structured_content):
        return None, None

    lesson_script = None
    if lesson.script_id:
        from src.api.models.tables import Script

        script = db.query(Script).filter(Script.script_id == lesson.script_id).first()
        if script and script.generate_output:
            gen_output = json.loads(script.generate_output)
            lesson_script = gen_output.get("lesson_script")

    return structured_content, lesson_script


def _normalize_structured_content_payload(
    payload: dict,
    *,
    lesson_id: str,
    course_id: Optional[str],
) -> dict:
    """Backfill required schema fields for older/new courseware lesson rows."""
    payload = dict(payload or {})
    payload["lesson_id"] = payload.get("lesson_id") or lesson_id
    if course_id and not payload.get("course_id"):
        payload["course_id"] = course_id

    pages = payload.get("pages")
    if isinstance(pages, list):
        normalized_pages = []
        for index, page in enumerate(pages, start=1):
          if not isinstance(page, dict):
              continue
          next_page = dict(page)
          next_page["lesson_id"] = next_page.get("lesson_id") or lesson_id
          if course_id and not next_page.get("course_id"):
              next_page["course_id"] = course_id
          next_page["page"] = int(next_page.get("page") or next_page.get("page_number") or index)
          normalized_pages.append(next_page)
        payload["pages"] = normalized_pages

    sections = payload.get("sections")
    if isinstance(sections, list):
        normalized_sections = []
        for index, section in enumerate(sections, start=1):
            if not isinstance(section, dict):
                continue
            next_section = dict(section)
            next_section["lesson_id"] = next_section.get("lesson_id") or lesson_id
            if course_id and not next_section.get("course_id"):
                next_section["course_id"] = course_id
            next_section["section_id"] = (
                next_section.get("section_id")
                or next_section.get("sectionId")
                or f"section-{index}"
            )
            next_section["name"] = next_section.get("name") or next_section.get("title") or f"第 {index} 页"
            normalized_sections.append(next_section)
        payload["sections"] = normalized_sections

    payload.setdefault("source_asset_ids", [])
    payload.setdefault("lesson_summary", "")
    payload.setdefault("knowledge_points", [])
    return payload


def _has_teaching_context(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    return bool(payload.get("pages") or payload.get("sections") or payload.get("knowledge_points"))


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


def _structured_content_from_slide_plan(
    slide_plan: dict,
    *,
    lesson_id: str,
    course_id: Optional[str],
    lesson_name: Optional[str],
) -> Optional[dict]:
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
        title = slide.get("title") or slide.get("heading") or slide.get("name") or f"第 {page_number} 页"
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

        pages.append(
            {
                "page_id": f"page-{page_number}",
                "course_id": course_id,
                "lesson_id": lesson_id,
                "section_id": section_id,
                "page": page_number,
                "title": title,
                "content": "\n".join([summary, *points]).strip(),
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
                "course_id": course_id,
                "lesson_id": lesson_id,
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

    deduped_points = list(dict.fromkeys([point for point in all_points if point]))
    return {
        "course_id": course_id,
        "lesson_id": lesson_id,
        "source_asset_ids": [],
        "lesson_summary": slide_plan.get("deck_title") or lesson_name or "",
        "pages": pages,
        "sections": sections,
        "knowledge_points": deduped_points,
        "metadata": {"source": "slide_plan"},
    }


def _build_qa_history(history_qa: Optional[list[dict]]) -> list[dict]:
    """Convert API-format history_qa into agent-compatible QAHistoryItem dicts."""
    if not history_qa:
        return []

    items = []
    for item in history_qa:
        items.append(
            {
                "question": item.get("question", ""),
                "answer": item.get("answer", ""),
                "understanding_level": item.get("understandingLevel") or item.get("understanding_level"),
                "current_section_id": item.get("currentSectionId") or item.get("current_section_id"),
                "current_page": item.get("currentPage") or item.get("current_page"),
            }
        )
    return items


def _extract_related_knowledge(agent_result: dict, fallback_section_id: Optional[str]) -> Optional[dict]:
    """Extract the primary related knowledge point from the agent result."""
    matched_kps = agent_result.get("matched_knowledge_points", [])
    if matched_kps:
        first = matched_kps[0]
        kp_name = first.get("knowledge_point", "")
        source_sections = first.get("source_section_ids", [])
        return {
            "knowledgeId": kp_name,
            "knowledgeName": kp_name,
            "relatedSectionId": source_sections[0] if source_sections else (fallback_section_id or ""),
        }

    references = agent_result.get("references", [])
    if references:
        first_ref = references[0]
        return {
            "knowledgeId": first_ref.get("source_name", ""),
            "knowledgeName": first_ref.get("source_name", ""),
            "relatedSectionId": first_ref.get("section_id") or fallback_section_id or "",
        }

    return None


_cached_llm = None


def _get_agent_llm():
    """Create an OpenHands LLM from the project's .env configuration.

    Returns None if the config is missing (agent will use placeholder fallback).
    """
    global _cached_llm
    if _cached_llm is not None:
        return _cached_llm

    import os

    api_key = os.getenv("LLM_API_KEY", "")
    base_url = os.getenv("LLM_BASE_URL", "")
    model = os.getenv("LLM_MODEL", "")

    if not api_key or api_key.lower() in ("test", "fake", "placeholder", ""):
        return None

    # LiteLLM requires provider prefix (e.g. "deepseek/deepseek-chat")
    # Detect from base_url first since LLM_PROVIDER may not match litellm's provider names
    litellm_model = model
    if "/" not in model:
        if "deepseek" in base_url.lower():
            litellm_model = f"deepseek/{model}"
        elif "openai" in base_url.lower() or base_url:
            litellm_model = f"openai/{model}"

    try:
        from openhands.sdk.llm import LLM

        _cached_llm = LLM(model=litellm_model, api_key=api_key, base_url=base_url or None)
        logger.info("Agent LLM configured: model=%s base_url=%s", litellm_model, base_url)
        return _cached_llm
    except Exception:
        logger.debug("Failed to create agent LLM, will use placeholder", exc_info=True)
        return None


def _build_fallback_response(question: str, error: Optional[str] = None) -> dict:
    """Return a minimal fallback when the agent cannot be invoked."""
    if error:
        answer = f"抱歉，系统暂时无法处理该问题（{error[:80]}），请稍后重试。"
    else:
        answer = "当前课时数据尚未生成，请教师先完成智课生成流程后再进行问答。"

    return {
        "answerId": generate_id("ans"),
        "answerContent": answer,
        "answerType": "text",
        "relatedKnowledge": None,
        "suggestions": ["请先完成智课生成", "尝试换一种方式提问"],
        "understandingLevel": "none",
        "questionType": "unknown",
        "recommendedNarrationLevel": None,
        "nextAction": None,
        "reason": "",
        "matchedSectionId": None,
        "matchedPage": None,
        "targetSectionId": None,
        "targetPage": None,
    }


def _normalize_agent_result(agent_result: Any) -> dict:
    """Coerce student-agent return value into the response_payload shape.

    Both the OpenHands path and the Claude path now return the dumped
    ``StudentAgentResponse`` (a flat dict).  Older intermediate shapes
    (``{"output": StudentAgentResponse, ...}``) are still accepted for
    forward compatibility.
    """
    if agent_result is None:
        return {}
    if hasattr(agent_result, "model_dump"):
        agent_result = agent_result.model_dump(mode="python")
    if not isinstance(agent_result, dict):
        return {}
    if "output" in agent_result and isinstance(agent_result["output"], dict):
        # Some legacy callers may surface the bundle dict from
        # build_student_agent_turn(); reach into output for the response.
        return agent_result["output"]
    if "output" in agent_result and hasattr(agent_result["output"], "model_dump"):
        return agent_result["output"].model_dump(mode="python")
    return agent_result


# ── game payload ────────────────────────────────────────────────────


def generate_game_payload(
    db: Session,
    *,
    lesson_id: str,
    session_id: str,
    question: str = "",
    current_section_id: Optional[str] = None,
    current_page: Optional[int] = None,
) -> Optional[dict]:
    """Generate one multiple-choice question grounded in the lesson.

    Used by ``POST /qa/gamePayload``.  Falls back to a deterministic stub
    when the lesson content is missing so the front end can still test
    rendering.
    """
    structured_content_dict, _ = _load_lesson_content(db, lesson_id)
    if structured_content_dict is None:
        return None

    try:
        from src.schemas.common import StructuredLessonContent
        from src.tools.game import GameAction, GameTool

        sc = StructuredLessonContent.model_validate(structured_content_dict)
        tool = GameTool(structured_content=sc)
        observation = tool.run(
            GameAction(
                mode="multiple_choice",
                question=question or "",
                lesson_id=sc.lesson_id,
                session_id=session_id,
                section_id=current_section_id,
                page=current_page,
            )
        )
        return {
            "gameType": observation.game_type,
            "prompt": observation.prompt,
            "choices": list(observation.choices),
            "correctIndex": observation.correct_index,
            "correctChoice": observation.correct_choice,
            "explanation": observation.explanation,
        }
    except Exception:
        logger.exception("generate_game_payload failed for lesson %s", lesson_id)
        return _build_stub_game_payload(structured_content_dict, current_section_id)


def _build_stub_game_payload(
    structured_content_dict: dict,
    current_section_id: Optional[str],
) -> dict:
    """Trivial deterministic game payload so the API never returns 500."""
    sections = structured_content_dict.get("sections", []) or []
    target = None
    for sec in sections:
        if sec.get("section_id") == current_section_id:
            target = sec
            break
    if target is None and sections:
        target = sections[0]
    if target is None:
        return {
            "gameType": "multiple_choice",
            "prompt": "本节没有足够的内容生成题目，请稍后再试。",
            "choices": ["稍后再来", "继续学习", "复习上节", "提个问题"],
            "correctIndex": 1,
            "correctChoice": "继续学习",
            "explanation": "课程数据正在准备中。",
        }
    name = target.get("name") or target.get("title") or "本节内容"
    kp = (target.get("key_points") or target.get("knowledge_points") or [name])[:1]
    answer = kp[0] if kp else name
    distractors = [s.get("name") or s.get("title") or "其他章节" for s in sections if s is not target][:3]
    while len(distractors) < 3:
        distractors.append(f"无关选项{len(distractors) + 1}")
    choices = [answer] + distractors
    return {
        "gameType": "multiple_choice",
        "prompt": f"以下哪一项最贴合“{name}”的核心要点？",
        "choices": choices,
        "correctIndex": 0,
        "correctChoice": answer,
        "explanation": f"{name} 的核心要点是 {answer}。",
    }


def voice_to_text(voice_url: str, language: str = "zh-CN") -> dict:
    """Call an OpenAI-compatible /audio/transcriptions endpoint.

    `voice_url` is a local filesystem path (saved by save_upload_file).
    Returns {text, confidence}. Falls back to a visible placeholder when
    ASR_API_KEY is missing or the upstream call fails so the UI can
    still surface a meaningful error to the user.
    """
    from pathlib import Path

    import httpx

    from src.api.config import settings

    api_key = (settings.ASR_API_KEY or "").strip()
    if not api_key:
        logger.warning("ASR_API_KEY is not configured; returning placeholder.")
        return {
            "text": "[未配置 ASR_API_KEY，无法识别]",
            "confidence": 0.0,
        }

    audio_path = Path(voice_url)
    if not audio_path.exists():
        logger.error("Audio file not found: %s", voice_url)
        return {"text": "", "confidence": 0.0}

    endpoint = settings.ASR_BASE_URL.rstrip("/") + "/audio/transcriptions"

    lang_map = {"zh-CN": "zh", "zh": "zh", "en-US": "en", "en": "en"}
    lang_short = lang_map.get(language, language.split("-")[0].lower() if language else "zh")

    try:
        with audio_path.open("rb") as audio_file:
            files = {"file": (audio_path.name, audio_file, "application/octet-stream")}
            data = {
                "model": settings.ASR_MODEL,
                "language": lang_short,
                "response_format": "json",
            }
            headers = {"Authorization": f"Bearer {api_key}"}

            with httpx.Client(timeout=settings.ASR_TIMEOUT_SECONDS) as client:
                response = client.post(endpoint, files=files, data=data, headers=headers)
                response.raise_for_status()
                payload = response.json()
    except httpx.HTTPStatusError as exc:
        logger.error("ASR HTTP error %s: %s", exc.response.status_code, exc.response.text)
        return {"text": "", "confidence": 0.0}
    except Exception as exc:  # noqa: BLE001
        logger.exception("ASR call failed: %s", exc)
        return {"text": "", "confidence": 0.0}

    text = (payload.get("text") or "").strip()
    return {"text": text, "confidence": 1.0 if text else 0.0}
