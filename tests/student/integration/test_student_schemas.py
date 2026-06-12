from pydantic import ValidationError

from src.schemas import (
    LearningProgress,
    LearningSession,
    QARecord,
    RetrievedContextItem,
    StudentAgentRequest,
    StudentAgentResponse,
    StructuredLessonContent,
)


def _build_structured_content() -> StructuredLessonContent:
    return StructuredLessonContent(
        course_id="COURSE_1",
        lesson_id="LESSON_1",
        lesson_summary="Sample lesson",
        pages=[
            {
                "page_id": "page_1",
                "lesson_id": "LESSON_1",
                "section_id": "sec_1",
                "page": 1,
                "title": "Hooke Law",
                "content": "Stress is proportional to strain within elastic limit.",
                "summary": "Hooke law summary",
                "key_points": ["stress", "strain"],
                "knowledge_points": ["Hooke law"],
                "page_role": "content",
            }
        ],
        sections=[
            {
                "section_id": "sec_1",
                "lesson_id": "LESSON_1",
                "name": "Elasticity",
                "summary": "Elasticity section",
                "page_range": [1],
                "key_points": ["stress", "strain"],
                "knowledge_points": ["Hooke law"],
                "section_type": "content",
            }
        ],
        knowledge_points=["Hooke law"],
    )


def test_student_agent_request_backfills_current_position_from_session_and_progress():
    request = StudentAgentRequest(
        lesson_id="LESSON_1",
        session_id="SESSION_1",
        question="什么是胡克定律？",
        structured_content=_build_structured_content(),
        session=LearningSession(
            session_id="SESSION_1",
            course_id="COURSE_1",
            lesson_id="LESSON_1",
            current_section_id="sec_1",
            current_page=1,
            current_script_block_id="script_1",
            progress_percent=12.5,
        ),
        progress=LearningProgress(
            session_id="SESSION_1",
            course_id="COURSE_1",
            lesson_id="LESSON_1",
            current_section_id="sec_1",
            current_page=1,
            current_script_block_id="script_1",
            progress_percent=12.5,
        ),
    )

    assert request.course_id == "COURSE_1"
    assert request.current_section_id == "sec_1"
    assert request.current_page == 1
    assert request.current_script_block_id == "script_1"


def test_student_agent_request_rejects_mismatched_session_lesson_id():
    try:
        StudentAgentRequest(
            lesson_id="LESSON_1",
            session_id="SESSION_1",
            question="为什么会这样？",
            structured_content=_build_structured_content(),
            session=LearningSession(
                session_id="SESSION_1",
                lesson_id="LESSON_2",
                progress_percent=0.0,
            ),
        )
    except ValidationError as exc:
        assert "session.lesson_id must match StudentAgentRequest.lesson_id" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for mismatched session.lesson_id")


def test_student_agent_response_rejects_mismatched_qa_record_identity():
    try:
        StudentAgentResponse(
            lesson_id="LESSON_1",
            session_id="SESSION_1",
            answer="胡克定律描述了弹性范围内应力与应变的线性关系。",
            qa_record=QARecord(
                qa_record_id="qa_1",
                lesson_id="LESSON_2",
                session_id="SESSION_1",
                question="什么是胡克定律？",
                answer="test",
            ),
        )
    except ValidationError as exc:
        assert "qa_record.lesson_id must match StudentAgentResponse.lesson_id" in str(exc)
    else:
        raise AssertionError("Expected ValidationError for mismatched qa_record.lesson_id")


def test_retrieved_context_item_matches_minimal_contract_shape():
    item = RetrievedContextItem(
        source="page",
        source_id="page_1",
        title="Hooke Law",
        text="Stress is proportional to strain within elastic limit.",
        section_id="sec_1",
        page=1,
        score=0.91,
    )

    assert item.source == "page"
    assert item.source_id == "page_1"
    assert item.section_id == "sec_1"
    assert item.page == 1
    assert item.score == 0.91
