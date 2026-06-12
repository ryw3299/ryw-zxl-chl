"""
Tests for response_builder.py - Student Agent Result Aggregation Layer
"""

import pytest

from src.agents.student.response_builder import (
    build_student_agent_response,
    extract_reference_items,
)
from src.schemas import (
    LearningProgress,
    LearningSession,
    ReferenceItem,
    RetrievedContextItem,
    StructuredLessonContent,
    StudentAgentRequest,
    StudentAgentResponse,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def minimal_request() -> StudentAgentRequest:
    """Create a minimal valid StudentAgentRequest for testing."""
    content = StructuredLessonContent(
        lesson_id="lesson_001",
        lesson_summary="测试课时摘要",
        pages=[],
        sections=[],
        knowledge_points=["知识点1", "知识点2"],
    )
    return StudentAgentRequest(
        lesson_id="lesson_001",
        session_id="session_001",
        question="什么是应力？",
        structured_content=content,
    )


@pytest.fixture
def minimal_qa_output() -> dict:
    """Create a minimal QA output dict."""
    return {
        "status": "success",
        "message": "qa stage finished",
        "answer": "应力是物体受到外力作用时产生的内力。",
        "references": [],
        "understanding_level": "full",
        "matched_section_id": "section_1",
        "matched_page": 1,
        "matched_script_block_id": None,
        "skill_name": "definition",
    }


@pytest.fixture
def minimal_decision_output() -> dict:
    """Create a minimal decision output dict."""
    return {
        "status": "success",
        "message": "decision stage finished",
        "next_action": "resume",
        "reason": "当前问题已得到覆盖，可以继续原进度。",
        "target_section_id": "section_1",
        "target_page": 1,
        "target_script_block_id": None,
    }


# ---------------------------------------------------------------------------
# extract_reference_items tests
# ---------------------------------------------------------------------------


class TestExtractReferenceItems:
    """Tests for extract_reference_items function."""

    def test_empty_list(self):
        """Empty input returns empty list."""
        result = extract_reference_items([])
        assert result == []

    def test_none_input(self):
        """None input returns empty list."""
        result = extract_reference_items(None)
        assert result == []

    def test_reference_item_list(self):
        """List of ReferenceItem objects passes through."""
        items = [
            ReferenceItem(source_type="lesson", source_name="Page 1", snippet="内容1"),
            ReferenceItem(source_type="script", source_name="Block 1", snippet="内容2"),
        ]
        result = extract_reference_items(items)
        assert len(result) == 2
        assert all(isinstance(r, ReferenceItem) for r in result)

    def test_dict_list(self):
        """List of dicts gets converted to ReferenceItem."""
        items = [
            {"source_type": "lesson", "source_name": "Page 1", "snippet": "内容1"},
            {"source_type": "faq", "source_name": "FAQ 1", "snippet": "内容2"},
        ]
        result = extract_reference_items(items)
        assert len(result) == 2
        assert all(isinstance(r, ReferenceItem) for r in result)

    def test_retrieved_context_item(self):
        """RetrievedContextItem gets converted to ReferenceItem."""
        items = [
            RetrievedContextItem(
                source="page",
                source_id="page_1",
                title="测试页面",
                text="这是页面内容",
                section_id="section_1",
                page=1,
                score=0.95,
            )
        ]
        result = extract_reference_items(items)
        assert len(result) == 1
        assert result[0].source_type == "lesson"  # page -> lesson conversion
        assert result[0].source_name == "测试页面"
        assert result[0].snippet == "这是页面内容"

    def test_script_block_conversion(self):
        """RetrievedContextItem with source=script_block converts to script type."""
        items = [
            RetrievedContextItem(
                source="script_block",
                source_id="block_1",
                title="脚本块1",
                text="这是脚本内容",
                section_id="section_1",
                page=1,
                score=0.9,
            )
        ]
        result = extract_reference_items(items)
        assert len(result) == 1
        assert result[0].source_type == "script"
        assert result[0].script_block_id == "block_1"

    def test_mixed_list(self):
        """Mixed list of types gets normalized."""
        items = [
            ReferenceItem(source_type="lesson", source_name="Page 1", snippet="内容1"),
            {"source_type": "faq", "source_name": "FAQ 1", "snippet": "内容2"},
            RetrievedContextItem(
                source="page",
                source_id="page_2",
                title="Page 2",
                text="内容3",
            ),
        ]
        result = extract_reference_items(items)
        assert len(result) == 3

    def test_none_items_filtered(self):
        """None items in list are filtered out."""
        items = [
            ReferenceItem(source_type="lesson", source_name="Page 1", snippet="内容1"),
            None,
            {"source_type": "faq", "source_name": "FAQ 1", "snippet": "内容2"},
        ]
        result = extract_reference_items(items)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# build_student_agent_response tests
# ---------------------------------------------------------------------------


class TestBuildStudentAgentResponse:
    """Tests for build_student_agent_response function."""

    def test_minimal_inputs(self, minimal_request, minimal_qa_output, minimal_decision_output):
        """Minimal valid inputs produce valid response."""
        response = build_student_agent_response(
            minimal_request,
            minimal_qa_output,
            minimal_decision_output,
        )

        assert isinstance(response, StudentAgentResponse)
        assert response.status == "success"
        assert response.answer == "应力是物体受到外力作用时产生的内力。"
        assert response.question_type == "definition"
        assert response.understanding_level == "full"
        assert response.next_action == "resume"
        assert response.matched_section_id == "section_1"
        assert response.matched_page == 1

    def test_request_as_dict(self, minimal_qa_output, minimal_decision_output):
        """Request as dict gets validated."""
        request_dict = {
            "lesson_id": "lesson_001",
            "session_id": "session_001",
            "question": "什么是应力？",
            "structured_content": {
                "lesson_id": "lesson_001",
                "lesson_summary": "测试摘要",
                "pages": [],
                "sections": [],
                "knowledge_points": [],
            },
        }
        response = build_student_agent_response(
            request_dict,
            minimal_qa_output,
            minimal_decision_output,
        )
        assert isinstance(response, StudentAgentResponse)

    def test_answer_extraction(self, minimal_request, minimal_decision_output):
        """Answer is correctly extracted from qa_output."""
        qa_output = {"answer": "自定义答案内容"}
        response = build_student_agent_response(
            minimal_request,
            qa_output,
            minimal_decision_output,
        )
        assert response.answer == "自定义答案内容"

    def test_references_extraction(self, minimal_request, minimal_decision_output):
        """References are correctly extracted and normalized."""
        qa_output = {
            "answer": "答案",
            "references": [
                {"source_type": "lesson", "source_name": "Page 1", "snippet": "内容1"},
                {"source_type": "faq", "source_name": "FAQ 1", "snippet": "内容2"},
            ],
        }
        response = build_student_agent_response(
            minimal_request,
            qa_output,
            minimal_decision_output,
        )
        assert len(response.references) == 2
        assert all(isinstance(r, ReferenceItem) for r in response.references)

    def test_matched_fields_fallback(self, minimal_request, minimal_qa_output, minimal_decision_output):
        """Matched fields fall back to request context when not in qa_output."""
        # qa_output has no matched fields, but request has current_section_id and current_page
        minimal_request.current_section_id = "context_section"
        minimal_request.current_page = 5

        qa_output = {"answer": "答案", "references": []}
        response = build_student_agent_response(
            minimal_request,
            qa_output,
            minimal_decision_output,
        )
        assert response.matched_section_id == "context_section"
        assert response.matched_page == 5

    def test_next_action_normalization(self, minimal_request, minimal_qa_output):
        """Next action string gets normalized to NextAction enum."""
        qa_output = {"answer": "答案", "references": []}
        decision_output = {"next_action": "reteach_slowly", "reason": "需要重讲"}
        response = build_student_agent_response(
            minimal_request,
            qa_output,
            decision_output,
        )
        assert response.next_action == "reteach_slowly"

    def test_updated_session_created(self, minimal_request, minimal_qa_output, minimal_decision_output):
        """Updated session is created from context."""
        response = build_student_agent_response(
            minimal_request,
            minimal_qa_output,
            minimal_decision_output,
        )
        assert response.updated_session is not None
        assert isinstance(response.updated_session, LearningSession)
        assert response.updated_session.session_id == "session_001"
        assert response.updated_session.current_section_id == "section_1"

    def test_updated_progress_created(self, minimal_request, minimal_qa_output, minimal_decision_output):
        """Updated progress is created from context."""
        response = build_student_agent_response(
            minimal_request,
            minimal_qa_output,
            minimal_decision_output,
        )
        assert response.updated_progress is not None
        assert isinstance(response.updated_progress, LearningProgress)
        assert response.updated_progress.session_id == "session_001"
        assert response.updated_progress.last_action == "resume"

    def test_qa_record_created(self, minimal_request, minimal_qa_output, minimal_decision_output):
        """QA record is created with correct fields."""
        response = build_student_agent_response(
            minimal_request,
            minimal_qa_output,
            minimal_decision_output,
        )
        assert response.qa_record is not None
        assert response.qa_record.lesson_id == "lesson_001"
        assert response.qa_record.session_id == "session_001"
        assert response.qa_record.question == "什么是应力？"
        assert response.qa_record.answer == "应力是物体受到外力作用时产生的内力。"

    def test_metadata_populated(self, minimal_request, minimal_qa_output, minimal_decision_output):
        """Metadata is populated with stage information."""
        response = build_student_agent_response(
            minimal_request,
            minimal_qa_output,
            minimal_decision_output,
        )
        assert response.metadata is not None
        assert response.metadata["qa_status"] == "success"
        assert response.metadata["skill_name"] == "definition"

    def test_custom_metadata_merged(self, minimal_request, minimal_qa_output, minimal_decision_output):
        """Custom metadata gets merged with default metadata."""
        custom_metadata = {"custom_field": "custom_value"}
        response = build_student_agent_response(
            minimal_request,
            minimal_qa_output,
            minimal_decision_output,
            metadata=custom_metadata,
        )
        assert response.metadata["custom_field"] == "custom_value"
        assert response.metadata["qa_status"] == "success"

    def test_suggested_questions_generated(self, minimal_request, minimal_qa_output, minimal_decision_output):
        """Suggested questions are generated when not provided."""
        response = build_student_agent_response(
            minimal_request,
            minimal_qa_output,
            minimal_decision_output,
        )
        assert len(response.suggested_questions) > 0
        assert all(isinstance(q, str) for q in response.suggested_questions)

    def test_suggested_questions_override(self, minimal_request, minimal_qa_output, minimal_decision_output):
        """Suggested questions can be overridden."""
        custom_questions = ["自定义问题1", "自定义问题2"]
        response = build_student_agent_response(
            minimal_request,
            minimal_qa_output,
            minimal_decision_output,
            suggested_questions=custom_questions,
        )
        assert response.suggested_questions == custom_questions

    def test_question_type_classification(self, minimal_request, minimal_decision_output):
        """Question type is auto-classified when not provided."""
        qa_output = {"answer": "答案", "references": []}
        response = build_student_agent_response(
            minimal_request,
            qa_output,
            minimal_decision_output,
        )
        # "什么是应力？" should be classified as "definition"
        assert response.question_type == "definition"

    def test_understanding_level_normalization(self, minimal_request, minimal_decision_output):
        """Understanding level string gets normalized to enum."""
        qa_output = {
            "answer": "答案",
            "references": [],
            "understanding_level": "partial",
        }
        response = build_student_agent_response(
            minimal_request,
            qa_output,
            minimal_decision_output,
        )
        assert response.understanding_level == "partial"

    def test_reason_extraction(self, minimal_request, minimal_qa_output):
        """Reason is correctly extracted from decision_output."""
        qa_output = {"answer": "答案", "references": []}
        decision_output = {"reason": "自定义原因文本"}
        response = build_student_agent_response(
            minimal_request,
            qa_output,
            decision_output,
        )
        assert response.reason == "自定义原因文本"

    def test_target_fields_fallback_to_matched(self, minimal_request, minimal_qa_output):
        """Target fields fall back to matched fields when not specified."""
        qa_output = {
            "answer": "答案",
            "references": [],
            "matched_section_id": "matched_section",
            "matched_page": 10,
            "matched_script_block_id": "matched_block",
        }
        decision_output = {"reason": "原因"}  # No target fields
        response = build_student_agent_response(
            minimal_request,
            qa_output,
            decision_output,
        )
        assert response.target_section_id == "matched_section"
        assert response.target_page == 10
        assert response.target_script_block_id == "matched_block"


# ---------------------------------------------------------------------------
# Round-trip test
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Test that response can be serialized and validated."""

    def test_response_serializable(self, minimal_request, minimal_qa_output, minimal_decision_output):
        """Response can be serialized to dict."""
        response = build_student_agent_response(
            minimal_request,
            minimal_qa_output,
            minimal_decision_output,
        )
        data = response.model_dump(mode="python")
        assert isinstance(data, dict)
        assert data["status"] == "success"
        assert "answer" in data
        assert "references" in data

    def test_response_validates_on_reload(self, minimal_request, minimal_qa_output, minimal_decision_output):
        """Serialized response can be re-validated."""
        response = build_student_agent_response(
            minimal_request,
            minimal_qa_output,
            minimal_decision_output,
        )
        data = response.model_dump(mode="python")
        reloaded = StudentAgentResponse.model_validate(data)
        assert reloaded.answer == response.answer
        assert reloaded.session_id == response.session_id
