from unittest.mock import MagicMock, patch

from openhands.sdk.llm import LLM, LLMResponse, Message, MessageToolCall, TextContent
from pydantic import SecretStr

from src.agents.student import build_student_agent_turn, run_student_agent
from src.agents.student.agent import (
    _decide_next_action_rule,
    _decide_next_action_via_llm,
    _is_placeholder_llm,
    _llm_synthesize_answer,
    _parse_llm_decision_response,
    ALLOWED_NEXT_ACTIONS,
)
from src.schemas import LearningProgress, LearningSession, StudentAgentRequest


def _make_mock_llm(completion_return_text: str) -> LLM:
    """Create a real LLM instance with a mocked completion method.

    Uses model_construct to bypass field validation, then patches completion
    to return the desired text without making real API calls.
    """
    mock_response = MagicMock(spec=LLMResponse)
    mock_response.id = "resp_mock"
    mock_response.message = Message(
        role="assistant",
        content=[TextContent(text=completion_return_text)],
    )
    mock_completion = MagicMock(return_value=mock_response)

    # Build a bare-minimum LLM via model_construct to avoid Pydantic
    # field-validation during construction (avoids network/validate-on-init side-effects).
    llm = LLM.model_construct(
        model="gpt-4o-mini",
        api_key=SecretStr("sk-test-mock-key"),
        base_url=None,
        api_version=None,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_region_name=None,
        openrouter_site_url=None,
        openrouter_app_name=None,
        litellm_extra_body={},
    )
    # completion is a regular method, set it via object.__setattr__ to bypass
    # Pydantic's frozen-model __setattr__
    object.__setattr__(llm, "completion", mock_completion)
    return llm


def _build_request() -> StudentAgentRequest:
    return StudentAgentRequest(
        course_id="COURSE_1",
        lesson_id="LESSON_1",
        session_id="SESSION_1",
        question="什么是应力？",
        structured_content={
            "course_id": "COURSE_1",
            "lesson_id": "LESSON_1",
            "lesson_summary": "材料力学基础",
            "pages": [
                {
                    "page_id": "page_1",
                    "lesson_id": "LESSON_1",
                    "section_id": "sec_1",
                    "page": 1,
                    "title": "应力基础",
                    "content": "应力表示单位面积上的内力。",
                    "summary": "应力是单位面积上的内力。",
                    "key_points": ["应力"],
                    "knowledge_points": ["应力"],
                    "page_role": "definition",
                }
            ],
            "sections": [
                {
                    "section_id": "sec_1",
                    "lesson_id": "LESSON_1",
                    "name": "基础概念",
                    "summary": "讲解应力的定义。",
                    "page_range": [1],
                    "key_points": ["应力"],
                    "knowledge_points": ["应力"],
                    "section_type": "content",
                }
            ],
            "knowledge_points": ["应力"],
        },
        session=LearningSession(
            session_id="SESSION_1",
            course_id="COURSE_1",
            lesson_id="LESSON_1",
            current_section_id="sec_1",
            current_page=1,
            current_script_block_id="script_1",
            progress_percent=20.0,
        ),
        progress=LearningProgress(
            session_id="SESSION_1",
            course_id="COURSE_1",
            lesson_id="LESSON_1",
            current_section_id="sec_1",
            current_page=1,
            current_script_block_id="script_1",
            progress_percent=20.0,
        ),
    )


def test_build_student_agent_turn_returns_structured_response():
    stages = build_student_agent_turn(_build_request())
    output = stages["output"]

    assert output.status == "success"
    assert output.answer
    assert output.question_type == "definition"
    assert output.next_action == "supplement_then_resume"
    assert output.updated_progress is not None
    assert output.updated_progress.last_action == "supplement_then_resume"
    assert output.qa_record is not None
    assert output.qa_record.question == "什么是应力？"
    assert output.references
    assert output.matched_knowledge_points


def test_run_student_agent_returns_plain_dict_payload():
    output = run_student_agent(_build_request())

    assert output["status"] == "success"
    assert output["lesson_id"] == "LESSON_1"
    assert output["session_id"] == "SESSION_1"
    assert output["updated_progress"]["last_action"] == output["next_action"]


# ---------------------------------------------------------------------------
# Tests for LLM-based decision
# ---------------------------------------------------------------------------


class TestParseLlmDecisionResponse:
    def test_parses_valid_action(self):
        raw = """ACTION: resume
REASON: 学生已理解当前内容
TARGET_SECTION: sec_1
TARGET_PAGE: 3
TARGET_SCRIPT_BLOCK: script_2"""
        result = _parse_llm_decision_response(
            raw,
            fallback_next_action="reteach_slowly",
            fallback_reason="fallback reason",
            matched_section_id="sec_default",
            matched_page=1,
            matched_script_block_id="script_default",
        )
        assert result["next_action"] == "resume"
        assert result["reason"] == "学生已理解当前内容"
        assert result["target_section_id"] == "sec_1"
        assert result["target_page"] == 3
        assert result["target_script_block_id"] == "script_2"
        assert result["decision_source"] == "llm"

    def test_guardrail_invalid_action_falls_back(self):
        raw = """ACTION: invalid_action
REASON: some reason
TARGET_SECTION: sec_1"""
        result = _parse_llm_decision_response(
            raw,
            fallback_next_action="reteach_slowly",
            fallback_reason="fallback reason",
            matched_section_id="sec_default",
            matched_page=1,
            matched_script_block_id="script_default",
        )
        assert result["next_action"] == "reteach_slowly"
        assert result["decision_source"] == "llm"

    def test_parses_trigger_game_action(self):
        raw = """ACTION: trigger_game
REASON: 通过游戏巩固理解
TARGET_SECTION: null
TARGET_PAGE: null
TARGET_SCRIPT_BLOCK: null"""
        result = _parse_llm_decision_response(
            raw,
            fallback_next_action="resume",
            fallback_reason="default reason",
            matched_section_id="sec_1",
            matched_page=2,
            matched_script_block_id="script_1",
        )
        assert result["next_action"] == "trigger_game"
        assert result["target_section_id"] == "sec_1"
        assert result["target_page"] == 2

    def test_partial_response_uses_fallback_targets(self):
        raw = """ACTION: supplement_then_resume
REASON: 需要补充"""
        result = _parse_llm_decision_response(
            raw,
            fallback_next_action="resume",
            fallback_reason="default",
            matched_section_id="sec_fallback",
            matched_page=5,
            matched_script_block_id="script_fallback",
        )
        assert result["next_action"] == "supplement_then_resume"
        assert result["target_section_id"] == "sec_fallback"
        assert result["target_page"] == 5
        assert result["target_script_block_id"] == "script_fallback"


class TestDecideNextActionRule:
    def test_none_understanding_returns_reteach_slowly(self):
        assert _decide_next_action_rule("definition", None) == "reteach_slowly"
        assert _decide_next_action_rule("definition", "none") == "reteach_slowly"

    def test_definition_question_returns_supplement_then_resume(self):
        assert _decide_next_action_rule("definition", "full") == "supplement_then_resume"
        assert _decide_next_action_rule("reasoning", "partial") == "supplement_then_resume"

    def test_other_question_types_return_resume(self):
        assert _decide_next_action_rule("procedure", "full") == "resume"
        assert _decide_next_action_rule("example", "full") == "resume"
        assert _decide_next_action_rule("comparison", "full") == "resume"
        assert _decide_next_action_rule("summary", "full") == "resume"


class TestAllowedNextActions:
    def test_all_allowed_actions_defined(self):
        assert "resume" in ALLOWED_NEXT_ACTIONS
        assert "supplement_then_resume" in ALLOWED_NEXT_ACTIONS
        assert "reteach_slowly" in ALLOWED_NEXT_ACTIONS
        assert "trigger_game" in ALLOWED_NEXT_ACTIONS
        assert len(ALLOWED_NEXT_ACTIONS) == 4


class TestLlmDecisionIntegration:
    def test_llm_valid_response_becomes_decision(self):
        """When LLM returns valid action, it flows through to response."""
        mock_decision = {
            "next_action": "trigger_game",
            "reason": "通过游戏巩固理解",
            "target_section_id": "sec_new",
            "target_page": 5,
            "target_script_block_id": None,
            "decision_source": "llm",
        }
        with patch(
            "src.agents.student.agent._decide_next_action_via_llm",
            return_value=mock_decision,
        ):
            stages = build_student_agent_turn(_build_request())
            output = stages["output"]

            assert output.next_action == "trigger_game"
            assert "游戏" in output.reason
            assert output.metadata.get("decision_source") == "llm"

    def test_guardrail_sanitizes_invalid_action_from_parsing(self):
        """When _parse_llm_decision_response produces invalid action, guardrail sanitizes."""
        # This tests the guardrail within _parse_llm_decision_response
        # by directly calling it with invalid action
        result = _parse_llm_decision_response(
            "ACTION: not_a_valid_action\nREASON: some reason",
            fallback_next_action="reteach_slowly",
            fallback_reason="fallback reason",
            matched_section_id="sec_1",
            matched_page=1,
            matched_script_block_id=None,
        )
        # Should fall back to the fallback_next_action
        assert result["next_action"] == "reteach_slowly"
        assert result["decision_source"] == "llm"

    def test_fallback_rule_when_llm_fails(self):
        """When LLM call fails, rule-based decision is used."""
        # Test _decide_next_action_via_llm directly with a failing LLM
        mock_llm = MagicMock()
        mock_llm.completion.side_effect = Exception("LLM API error")
        mock_llm.api_key = MagicMock()
        mock_llm.api_key.get_secret_value.return_value = "mock-key"

        result = _decide_next_action_via_llm(
            request=_build_request(),
            question="什么是应力？",
            question_type="definition",
            understanding_level="full",
            matched_section_id="sec_1",
            matched_page=1,
            matched_script_block_id="script_1",
            history_records=[],
            llm=mock_llm,
        )

        # Should fall back to rule-based decision
        assert result["next_action"] in ALLOWED_NEXT_ACTIONS
        assert result["decision_source"] == "fallback_rule"

    def test_decision_source_in_metadata(self):
        """decision_source should be present in response metadata."""
        # Use the fallback path - when LLM fails internally
        mock_llm = MagicMock()
        mock_llm.completion.side_effect = Exception("LLM error")
        mock_llm.api_key = MagicMock()
        mock_llm.api_key.get_secret_value.return_value = "mock-key"

        result = _decide_next_action_via_llm(
            request=_build_request(),
            question="什么是应力？",
            question_type="definition",
            understanding_level="full",
            matched_section_id="sec_1",
            matched_page=1,
            matched_script_block_id="script_1",
            history_records=[],
            llm=mock_llm,
        )

        assert "decision_source" in result
        assert result["decision_source"] == "fallback_rule"


# ---------------------------------------------------------------------------
# Tests for answer synthesis
# ---------------------------------------------------------------------------

class TestLlmSynthesizeAnswer:
    """Tests for _llm_synthesize_answer."""

    def test_returns_llm_text_when_non_empty(self):
        """When LLM returns non-empty text, it should be used as the answer."""
        mock_llm = MagicMock(spec=LLM)
        mock_llm.api_key = MagicMock()
        mock_llm.api_key.get_secret_value.return_value = "mock-api-key"
        mock_response = MagicMock(spec=LLMResponse)
        mock_response.message = Message(
            role="assistant",
            content=[TextContent(text="这是来自LLM的回答。")],
        )
        mock_llm.completion.return_value = mock_response

        answer, source = _llm_synthesize_answer(
            llm=mock_llm,
            question="什么是应力？",
            question_type="definition",
            skill_name="definition",
            exact_item=None,
            candidates=[],
            history_records=[],
            fallback_answer="这是回退答案。",
        )

        assert source == "llm"
        assert answer == "这是来自LLM的回答。"

    def test_falls_back_on_completion_exception(self):
        """When LLM raises an exception, falls back to rule-based answer."""
        mock_llm = MagicMock(spec=LLM)
        mock_llm.api_key = MagicMock()
        mock_llm.api_key.get_secret_value.return_value = "mock-key"
        mock_llm.completion.side_effect = RuntimeError("API call failed")

        answer, source = _llm_synthesize_answer(
            llm=mock_llm,
            question="什么是应力？",
            question_type="definition",
            skill_name="definition",
            exact_item=None,
            candidates=[],
            history_records=[],
            fallback_answer="这是回退答案。",
        )

        assert source == "fallback_rule"
        assert answer == "这是回退答案。"

    def test_falls_back_when_response_is_empty(self):
        """When LLM returns empty/whitespace text, falls back to rule-based answer."""
        mock_llm = MagicMock(spec=LLM)
        mock_llm.api_key = MagicMock()
        mock_llm.api_key.get_secret_value.return_value = "mock-key"
        mock_response = MagicMock(spec=LLMResponse)
        mock_response.message = Message(
            role="assistant",
            content=[TextContent(text="   ")],
        )
        mock_llm.completion.return_value = mock_response

        answer, source = _llm_synthesize_answer(
            llm=mock_llm,
            question="什么是应力？",
            question_type="definition",
            skill_name="definition",
            exact_item=None,
            candidates=[],
            history_records=[],
            fallback_answer="这是回退答案。",
        )

        assert source == "fallback_rule"
        assert answer == "这是回退答案。"

    def test_falls_back_when_placeholder_llm(self):
        """When LLM has placeholder API key, falls back without calling LLM."""
        mock_llm = MagicMock(spec=LLM)
        mock_llm.api_key = MagicMock()
        mock_llm.api_key.get_secret_value.return_value = "test"

        answer, source = _llm_synthesize_answer(
            llm=mock_llm,
            question="什么是应力？",
            question_type="definition",
            skill_name="definition",
            exact_item=None,
            candidates=[],
            history_records=[],
            fallback_answer="这是回退答案。",
        )

        mock_llm.completion.assert_not_called()
        assert source == "fallback_rule"
        assert answer == "这是回退答案。"


class TestIsPlaceholderLlm:
    """Tests for _is_placeholder_llm."""

    def test_detects_test_key(self):
        mock_llm = MagicMock(spec=LLM)
        mock_llm.api_key = MagicMock()
        mock_llm.api_key.get_secret_value.return_value = "test"
        assert _is_placeholder_llm(mock_llm) is True

    def test_detects_fake_key(self):
        mock_llm = MagicMock(spec=LLM)
        mock_llm.api_key = MagicMock()
        mock_llm.api_key.get_secret_value.return_value = "fake"
        assert _is_placeholder_llm(mock_llm) is True

    def test_detects_empty_key(self):
        mock_llm = MagicMock(spec=LLM)
        mock_llm.api_key = MagicMock()
        mock_llm.api_key.get_secret_value.return_value = ""
        assert _is_placeholder_llm(mock_llm) is True

    def test_accepts_real_key(self):
        mock_llm = MagicMock(spec=LLM)
        mock_llm.api_key = MagicMock()
        mock_llm.api_key.get_secret_value.return_value = "sk-ant-..."
        assert _is_placeholder_llm(mock_llm) is False

    def test_accepts_openai_key(self):
        mock_llm = MagicMock(spec=LLM)
        mock_llm.api_key = MagicMock()
        mock_llm.api_key.get_secret_value.return_value = "sk-02..."
        assert _is_placeholder_llm(mock_llm) is False


class TestAnswerSourceInFinalResponse:
    """Verify answer_source appears in qa_output and flows to final response."""

    def test_answer_source_llm_in_qa_output(self):
        """When mock LLM returns valid answer, qa_output has answer_source=llm."""
        mock_llm = _make_mock_llm("LLM生成的答案：应力是材料内部由于外力作用而产生的内力。")

        request = _build_request()
        stages = build_student_agent_turn(request, llm=mock_llm)

        assert stages["qa_output"].get("answer_source") == "llm"
        assert "LLM生成的答案" in stages["qa_output"]["answer"]

    def test_answer_source_fallback_in_qa_output(self):
        """When placeholder LLM is used, qa_output has answer_source=fallback_rule."""
        request = _build_request()
        stages = build_student_agent_turn(request)
        assert stages["qa_output"].get("answer_source") == "fallback_rule"

    def test_llm_answer_in_final_response(self):
        """When mock LLM returns valid answer, that answer appears in final output."""
        mock_llm = _make_mock_llm("LLM答案内容。")

        request = _build_request()
        stages = build_student_agent_turn(request, llm=mock_llm)

        assert "LLM答案内容" in stages["output"].answer
        assert stages["output"].status == "success"

    def test_tools_still_called_with_llm(self):
        """Even with LLM-driven answer, tools are executed (grounding preserved)."""
        mock_llm = _make_mock_llm("LLM答案。")

        request = _build_request()
        stages = build_student_agent_turn(request, llm=mock_llm)

        # Tools should have been called (at least search and session)
        tool_names = [t["tool"] for t in stages["tool_trace"]]
        assert "search" in tool_names
        assert "session" in tool_names


def test_non_placeholder_llm_can_drive_openhands_tool_loop():
    first_response = MagicMock(spec=LLMResponse)
    first_response.id = "resp_1"
    first_response.message = Message(
        role="assistant",
        content=[TextContent(text="I will inspect the session and search the lesson first.")],
        tool_calls=[
            MessageToolCall(
                id="call_session",
                name="session",
                arguments='{"command":"get","session_id":"SESSION_1"}',
                origin="completion",
            ),
            MessageToolCall(
                id="call_search",
                name="search",
                arguments='{"query":"what is stress","top_k":3,"include_script":true}',
                origin="completion",
            ),
        ],
    )

    second_response = MagicMock(spec=LLMResponse)
    second_response.id = "resp_2"
    second_response.message = Message(
        role="assistant",
        content=[
            TextContent(
                text='{"answer":"Stress is the internal force per unit area.","question_type":"definition","understanding_level":"full","next_action":"resume","reason":"The lesson evidence is sufficient to continue.","matched_section_id":"sec_1","matched_page":1,"matched_script_block_id":null,"target_section_id":"sec_1","target_page":1,"target_script_block_id":null}'
            )
        ],
    )

    llm = LLM.model_construct(
        model="gpt-4o-mini",
        api_key=SecretStr("sk-real-ish-key"),
        base_url=None,
        api_version=None,
        aws_access_key_id=None,
        aws_secret_access_key=None,
        aws_region_name=None,
        openrouter_site_url=None,
        openrouter_app_name=None,
        litellm_extra_body={},
    )
    object.__setattr__(llm, "completion", MagicMock(side_effect=[first_response, second_response]))

    stages = build_student_agent_turn(_build_request(), llm=llm)

    assert stages["qa_output"]["answer_source"] == "llm_agent"
    assert stages["decision_output"]["decision_source"] == "llm_agent"
    tool_names = [t["tool"] for t in stages["tool_trace"]]
    assert "session" in tool_names
    assert "search" in tool_names
