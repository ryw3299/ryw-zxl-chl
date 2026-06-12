"""
OpenHands Response Builder - Student Agent Result Aggregation Layer

This module provides a clean interface for building StudentAgentResponse from
OpenHands conversation events (messages, actions, observations).

This layer is NOT an OpenHands tool nor the agent主体. It is the "结果收口层"
(result aggregation layer) that extracts and assembles the fields needed for
StudentAgentResponse.

Key exports:
    - build_student_agent_response(): Main entry point for building StudentAgentResponse
    - extract_reference_items(): Extract ReferenceItem list from various input formats
"""

from __future__ import annotations

from typing import Any, Optional, Union
from uuid import uuid4

from src.schemas import (
    KnowledgePointMatch,
    LearningProgress,
    LearningSession,
    NextAction,
    QARecord,
    ReferenceItem,
    RetrievedContextItem,
    StudentAgentRequest,
    StudentAgentResponse,
    StudentQuestionType,
    UnderstandingLevel,
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_student_agent_response(
    request: Union[StudentAgentRequest, dict[str, Any]],
    qa_output: dict[str, Any],
    decision_output: dict[str, Any],
    *,
    matched_knowledge_points: Optional[list[KnowledgePointMatch]] = None,
    suggested_questions: Optional[list[str]] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> StudentAgentResponse:
    """
    Build a complete StudentAgentResponse from QA and decision stage outputs.

    Args:
        request: The original StudentAgentRequest (or dict)
        qa_output: Dict containing at minimum:
            - answer (str): The generated answer
            - references (List[Dict|ReferenceItem]): Grounding references
            - understanding_level (str|UnderstandingLevel, optional)
            - matched_section_id (str, optional)
            - matched_page (int, optional)
            - matched_script_block_id (str, optional)
            - status (str, optional)
            - message (str, optional)
            - skill_name (str, optional)
        decision_output: Dict containing at minimum:
            - next_action (str|NextAction, optional)
            - reason (str, optional)
            - target_section_id (str, optional)
            - target_page (int, optional)
            - target_script_block_id (str, optional)
            - status (str, optional)
            - message (str, optional)
        matched_knowledge_points: Optional list of KnowledgePointMatch.
            If None, will be built from matched fields.
        suggested_questions: Optional list of suggested follow-up questions.
            If None, will be generated from question type.
        metadata: Optional additional metadata to attach to response.

    Returns:
        StudentAgentResponse: Fully assembled response with all fields populated
            according to schema validation.

    Raises:
        ValueError: If required fields are missing or validation fails.

    Example:
        >>> qa_output = {"answer": "...", "references": [...], "matched_section_id": "s1"}
        >>> decision_output = {"next_action": "resume", "reason": "..."}
        >>> response = build_student_agent_response(request, qa_output, decision_output)
    """
    # Validate and normalize request
    if isinstance(request, dict):
        validated_request = StudentAgentRequest.model_validate(request)
    else:
        validated_request = request

    # Extract and normalize basic fields
    course_id = validated_request.course_id
    lesson_id = validated_request.lesson_id
    session_id = validated_request.session_id

    # Extract answer
    answer = qa_output.get("answer", "")

    # Extract and convert references
    references = extract_reference_items(qa_output.get("references", []))

    # Extract question type
    question_type = qa_output.get("question_type") or _classify_question_type(validated_request.question)

    # Extract understanding level
    understanding_level_raw = qa_output.get("understanding_level")
    understanding_level = _normalize_understanding_level(understanding_level_raw)
    recommended_narration_level = qa_output.get("recommended_narration_level")

    # Extract matched fields (fall back to request context)
    matched_section_id = qa_output.get("matched_section_id") or validated_request.current_section_id
    matched_page = (
        qa_output.get("matched_page")
        if qa_output.get("matched_page") is not None
        else validated_request.current_page
    )
    matched_script_block_id = (
        qa_output.get("matched_script_block_id") or validated_request.current_script_block_id
    )

    # Extract decision fields
    next_action_raw = decision_output.get("next_action")
    next_action = _normalize_next_action(next_action_raw)
    reason = decision_output.get("reason", "")

    # Target fields (fall back to matched fields)
    target_section_id = decision_output.get("target_section_id") or matched_section_id
    target_page = (
        decision_output.get("target_page") if decision_output.get("target_page") is not None else matched_page
    )
    target_script_block_id = decision_output.get("target_script_block_id") or matched_script_block_id

    # Build knowledge point matches if not provided
    if matched_knowledge_points is None:
        matched_knowledge_points = _build_knowledge_point_matches_from_context(
            validated_request,
            matched_section_id=matched_section_id,
            matched_page=matched_page,
            matched_script_block_id=matched_script_block_id,
        )

    # Build suggested questions if not provided
    if suggested_questions is None:
        suggested_questions = _build_suggested_questions(question_type, matched_knowledge_points)

    # Build updated session
    updated_session = _build_updated_session_from_context(
        validated_request,
        target_section_id=target_section_id,
        target_page=target_page,
        target_script_block_id=target_script_block_id,
    )

    # Build updated progress
    updated_progress = _build_updated_progress_from_context(
        validated_request,
        next_action=next_action,
        target_section_id=target_section_id,
        target_page=target_page,
        target_script_block_id=target_script_block_id,
    )

    # Build QA record
    qa_record = _build_qa_record_from_context(
        validated_request,
        answer=answer,
        understanding_level=understanding_level,
        references=references,
    )

    # Assemble metadata
    response_metadata = metadata or {}
    response_metadata.update(
        {
            "qa_status": qa_output.get("status"),
            "qa_message": qa_output.get("message"),
            "decision_status": decision_output.get("status"),
            "decision_message": decision_output.get("message"),
            "decision_source": decision_output.get("decision_source"),
            "skill_name": qa_output.get("skill_name"),
        }
    )

    return StudentAgentResponse(
        status="success",
        message="student agent turn finished",
        course_id=course_id,
        lesson_id=lesson_id,
        session_id=session_id,
        answer=answer,
        references=references,
        question_type=question_type,
        understanding_level=understanding_level,
        recommended_narration_level=recommended_narration_level,
        next_action=next_action,
        reason=reason,
        matched_knowledge_points=matched_knowledge_points,
        matched_section_id=matched_section_id,
        matched_page=matched_page,
        matched_script_block_id=matched_script_block_id,
        target_section_id=target_section_id,
        target_page=target_page,
        target_script_block_id=target_script_block_id,
        suggested_questions=suggested_questions,
        updated_session=updated_session,
        updated_progress=updated_progress,
        qa_record=qa_record,
        metadata=response_metadata,
    )


def extract_reference_items(
    items: Union[list[dict[str, Any]], list[ReferenceItem], list[Any]],
) -> list[ReferenceItem]:
    """
    Extract and normalize a list of ReferenceItem from various input formats.

    Handles:
        - List[ReferenceItem]: Return as-is after validation
        - List[Dict]: Convert each dict to ReferenceItem
        - List[RetrievedContextItem]: Convert to ReferenceItem
        - Mixed list: Try to convert each item
        - Empty list: Return empty list

    Args:
        items: List of reference items in various formats.

    Returns:
        List[ReferenceItem]: Normalized list of ReferenceItem.

    Example:
        >>> refs = [{"source_type": "lesson", "source_name": "Page 1", "snippet": "..."}]
        >>> extract_reference_items(refs)
        [ReferenceItem(source_type="lesson", source_name="Page 1", ...)]
    """
    if not items:
        return []

    result: list[ReferenceItem] = []
    for item in items:
        if item is None:
            continue
        try:
            if isinstance(item, ReferenceItem):
                result.append(item)
            elif isinstance(item, RetrievedContextItem):
                result.append(_retrieved_context_to_reference(item))
            elif isinstance(item, dict):
                result.append(ReferenceItem.model_validate(item))
            else:
                # Try dict conversion for unknown types
                if hasattr(item, "model_dump"):
                    result.append(ReferenceItem.model_validate(item.model_dump()))
                elif hasattr(item, "__dict__"):
                    result.append(ReferenceItem.model_validate(vars(item)))
        except Exception:
            # Skip items that can't be converted
            continue

    return result


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _classify_question_type(question: str) -> StudentQuestionType:
    """Classify question type based on keywords (delegates to shared module)."""
    from src.utils.student.question_classifier import classify_question_type

    return classify_question_type(question)


def _normalize_understanding_level(value: Optional[Any]) -> Optional[UnderstandingLevel]:
    """Normalize understanding level to Literal value."""
    if value is None:
        return None
    if isinstance(value, str):
        value_lower = value.lower()
        if value_lower in ("full", "partial", "none"):
            return value_lower  # type: ignore
    return None


def _normalize_next_action(value: Optional[Any]) -> Optional[NextAction]:
    """Normalize next action to Literal value."""
    if value is None:
        return None
    if isinstance(value, str):
        value_lower = value.lower()
        if value_lower in ("resume", "supplement_then_resume", "reteach_slowly", "trigger_game"):
            return value_lower  # type: ignore
    return None


def _retrieved_context_to_reference(item: RetrievedContextItem) -> ReferenceItem:
    """Convert a RetrievedContextItem to ReferenceItem."""
    source_type = "script" if item.source == "script_block" else "lesson"
    return ReferenceItem(
        source_type=source_type,
        source_name=item.title or item.source_id,
        section_id=item.section_id,
        script_block_id=item.source_id if item.source == "script_block" else None,
        page=item.page,
        snippet=_clean_text(item.text, limit=160),
        score=item.score,
    )


def _clean_text(text: str, limit: int = 220) -> str:
    """Clean and optionally truncate text."""
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _build_knowledge_point_matches_from_context(
    request: StudentAgentRequest,
    matched_section_id: Optional[str],
    matched_page: Optional[int],
    matched_script_block_id: Optional[str],
) -> list[KnowledgePointMatch]:
    """Build knowledge point matches from request context and matched fields."""
    points: list[KnowledgePointMatch] = []
    seen: set[str] = set()

    def add_point(name: str, source_section_ids: list[str], source_pages: list[int], rationale: str) -> None:
        normalized_name = name.strip()
        if not normalized_name or normalized_name in seen:
            return
        seen.add(normalized_name)
        points.append(
            KnowledgePointMatch(
                knowledge_point=normalized_name,
                source_section_ids=source_section_ids,
                source_pages=source_pages,
                source_script_block_ids=[matched_script_block_id] if matched_script_block_id else [],
                rationale=rationale,
            )
        )

    sc = request.structured_content
    if sc is not None and matched_page is not None:
        for page in sc.pages:
            if page.page == matched_page:
                for kp in page.knowledge_points or page.key_points:
                    add_point(
                        kp,
                        [page.section_id] if page.section_id else [],
                        [page.page],
                        "Matched from the primary lesson page used in this answer.",
                    )
                break

    if sc is not None and matched_section_id is not None:
        for section in sc.sections:
            if section.section_id == matched_section_id:
                for kp in section.knowledge_points or section.key_points:
                    add_point(
                        kp,
                        [section.section_id],
                        list(section.page_range),
                        "Matched from the primary teaching section related to this answer.",
                    )
                break

    if not points and sc is not None:
        for item in sc.knowledge_points[:3]:
            add_point(
                item,
                [matched_section_id] if matched_section_id else [],
                [matched_page] if matched_page is not None else [],
                "Fallback knowledge point match from lesson-level knowledge points.",
            )

    return points


def _build_suggested_questions(
    question_type: StudentQuestionType,
    matched_knowledge_points: list[KnowledgePointMatch],
) -> list[str]:
    """Build suggested follow-up questions based on question type."""
    topic = matched_knowledge_points[0].knowledge_point if matched_knowledge_points else "这个知识点"
    suggestions_by_type = {
        "definition": [f"{topic}为什么重要？", f"{topic}可以怎么应用？"],
        "reasoning": [f"{topic}的前提条件是什么？", f"能不能举个例子解释 {topic}？"],
        "procedure": [f"{topic}每一步为什么这样做？", f"{topic}有哪些常见错误？"],
        "example": [f"{topic}还有别的例子吗？", f"{topic}和相近概念有什么区别？"],
        "comparison": [f"{topic}各自适合什么场景？", f"{topic}的核心差异能再总结一下吗？"],
        "summary": [f"{topic}里最关键的点是什么？", f"我该怎么检查自己是否真的理解了 {topic}？"],
        "unknown": [f"{topic}对应课件的哪一部分？", f"{topic}能再换一种方式解释吗？"],
    }
    return suggestions_by_type.get(question_type, suggestions_by_type["unknown"])


def _build_updated_session_from_context(
    request: StudentAgentRequest,
    target_section_id: Optional[str],
    target_page: Optional[int],
    target_script_block_id: Optional[str],
) -> LearningSession:
    """Build updated learning session from context and target fields."""
    base = request.session or LearningSession(
        session_id=request.session_id,
        course_id=request.course_id,
        lesson_id=request.lesson_id,
        current_section_id=request.current_section_id,
        current_page=request.current_page,
        current_script_block_id=request.current_script_block_id,
        progress_percent=request.progress.progress_percent if request.progress else 0.0,
    )
    return LearningSession(
        session_id=base.session_id,
        course_id=base.course_id or request.course_id,
        lesson_id=base.lesson_id,
        user_id=base.user_id,
        status=base.status,
        current_section_id=target_section_id or base.current_section_id,
        current_page=target_page if target_page is not None else base.current_page,
        current_script_block_id=target_script_block_id or base.current_script_block_id,
        progress_percent=base.progress_percent,
    )


def _build_updated_progress_from_context(
    request: StudentAgentRequest,
    next_action: Optional[NextAction],
    target_section_id: Optional[str],
    target_page: Optional[int],
    target_script_block_id: Optional[str],
) -> LearningProgress:
    """Build updated learning progress from context and target fields."""
    base = request.progress or LearningProgress(
        session_id=request.session_id,
        course_id=request.course_id,
        lesson_id=request.lesson_id,
        current_section_id=request.current_section_id,
        current_page=request.current_page,
        current_script_block_id=request.current_script_block_id,
        progress_percent=request.session.progress_percent if request.session else 0.0,
    )
    return LearningProgress(
        session_id=base.session_id,
        course_id=base.course_id or request.course_id,
        lesson_id=base.lesson_id,
        current_section_id=target_section_id or base.current_section_id,
        current_page=target_page if target_page is not None else base.current_page,
        current_script_block_id=target_script_block_id or base.current_script_block_id,
        progress_percent=base.progress_percent,
        last_action=next_action,
    )


def _build_qa_record_from_context(
    request: StudentAgentRequest,
    answer: str,
    understanding_level: Optional[UnderstandingLevel],
    references: list[ReferenceItem],
) -> QARecord:
    """Build QA record from context and answer details."""
    return QARecord(
        qa_record_id=f"qa_{uuid4().hex[:12]}",
        course_id=request.course_id,
        lesson_id=request.lesson_id,
        session_id=request.session_id,
        current_section_id=request.current_section_id,
        current_page=request.current_page,
        question=request.question,
        answer=answer,
        understanding_level=understanding_level,
        references=references,
    )
