"""Tests for OpenHands tool adapters.

These tests verify that the OpenHands tool adapters:
1. Can be instantiated via create() with injected dependencies
2. Return Sequence[ToolDefinition]
3. Support explicit dependency injection via **params
4. Produce valid Observation.content (list of TextContent)
5. Executor delegates to underlying business tools
6. Explicitly fail when required dependencies are missing
"""

import os
import tempfile

import pytest

from src.schemas import (
    LearningSession,
    PageBlock,
    ScriptBlock,
    SectionBlock,
    StructuredLessonContent,
)
from src.schemas.generate_schemas import LessonScript

# ---------------------------------------------------------------------------
# Shared test data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def structured_content():
    """Minimal StructuredLessonContent for testing."""
    pages = [
        PageBlock(
            page_id="page-1",
            course_id="course-test",
            lesson_id="lesson-test",
            section_id="section-1",
            page=1,
            title="Introduction to Python",
            content="Python is a high-level programming language.",
            summary="Overview",
            key_points=["high-level"],
            knowledge_points=["Python basics"],
            page_role="cover",
        ),
        PageBlock(
            page_id="page-2",
            course_id="course-test",
            lesson_id="lesson-test",
            section_id="section-1",
            page=2,
            title="Python Syntax",
            content="Python uses indentation to define code blocks.",
            summary="Syntax basics",
            key_points=["indentation"],
            knowledge_points=["Python syntax"],
            page_role="content",
        ),
    ]
    sections = [
        SectionBlock(
            section_id="section-1",
            course_id="course-test",
            lesson_id="lesson-test",
            name="Python Basics",
            summary="Introduction",
            page_range=[1, 2],
            key_points=["syntax"],
            knowledge_points=["Python basics"],
            section_type="intro",
        ),
    ]
    return StructuredLessonContent(
        course_id="course-test",
        lesson_id="lesson-test",
        source_asset_ids=["asset-1"],
        lesson_summary="A Python lesson.",
        pages=pages,
        sections=sections,
        knowledge_points=["Python basics"],
    )


@pytest.fixture
def lesson_script():
    """Minimal LessonScript for testing."""
    blocks = [
        ScriptBlock(
            script_block_id="block-1",
            course_id="course-test",
            lesson_id="lesson-test",
            section_id="section-1",
            title="Opening",
            script_text="Welcome to Python lesson.",
            key_points=["welcome"],
            block_type="opening",
            page_range=[1],
        ),
    ]
    return LessonScript(
        lesson_title="Python Lesson",
        script_blocks=blocks,
        metadata={"lesson_id": "lesson-test"},
    )


@pytest.fixture
def session_store():
    """Temp SessionStore for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_sessions.db")
        from src.memory.session_store import SessionStore

        yield SessionStore(db_path=db_path)


@pytest.fixture
def qa_history_store():
    """Temp QAHistoryStore for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_qa_history.db")
        from src.memory.history import QAHistoryStore

        yield QAHistoryStore(db_path=db_path)


@pytest.fixture
def sample_session(session_store):
    """Create and persist a LearningSession."""
    session = LearningSession(
        session_id="test-session-001",
        course_id="course-test",
        lesson_id="lesson-test",
        user_id="student-001",
        status="active",
        current_section_id="section-1",
        current_page=1,
        progress_percent=0.0,
    )
    return session_store.save(session)


# ---------------------------------------------------------------------------
# SearchOpenHandsTool Tests
# ---------------------------------------------------------------------------


class TestSearchOpenHandsTool:
    """Test SearchOpenHandsTool creation, injection, and execution."""

    def test_create_returns_sequence(self, structured_content, lesson_script):
        """Verify create() returns a Sequence of ToolDefinition."""
        from src.tools.openhands.search_tool import SearchOpenHandsTool

        tools = SearchOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        assert isinstance(tools, list)
        assert len(tools) == 1
        assert hasattr(tools[0], "executor")

    def test_tool_has_required_attributes(self, structured_content, lesson_script):
        """Verify ToolDefinition has required OpenHands attributes."""
        from src.tools.openhands.search_tool import SearchOpenHandsTool

        tools = SearchOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        tool = tools[0]

        assert tool.name == "search"
        assert hasattr(tool, "action_type")
        assert hasattr(tool, "observation_type")
        assert tool.executor is not None

    def test_action_schema_fields(self):
        """Verify SearchAction has expected fields."""
        from src.tools.openhands.search_tool import SearchAction

        action = SearchAction(query="test query")
        assert action.query == "test query"
        assert action.top_k == 5
        assert action.include_script is True

    def test_observation_content_is_text_content_list(self, structured_content, lesson_script):
        """Verify SearchObservation.content is list[TextContent], not list[dict]."""
        from src.tools.openhands.search_tool import SearchAction, SearchOpenHandsTool

        tools = SearchOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        executor = tools[0].executor

        action = SearchAction(query="Python")
        obs = executor(action)

        # Content must be list of TextContent
        assert isinstance(obs.content, list)
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in obs.content)
        # And must have readable text
        assert len(obs.content) > 0

    def test_executor_with_injected_deps_returns_valid_obs(self, structured_content, lesson_script):
        """Verify executor returns valid observation with LLM-readable content."""
        from src.tools.openhands.search_tool import SearchAction, SearchOpenHandsTool

        tools = SearchOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        executor = tools[0].executor

        action = SearchAction(query="Python")
        obs = executor(action)

        assert obs.total >= 0
        assert isinstance(obs.content, list)
        # Content text should mention results
        content_text = obs.content[0].text if obs.content else ""
        assert (
            "result" in content_text.lower()
            or "found" in content_text.lower()
            or "no" in content_text.lower()
        )

    def test_create_fails_without_structured_content(self):
        """Verify create() fails explicitly when structured_content is missing."""
        from src.tools.openhands.search_tool import SearchOpenHandsTool

        with pytest.raises(ValueError) as exc_info:
            SearchOpenHandsTool.create()

        assert "structured_content" in str(exc_info.value)


class TestGameOpenHandsTool:
    def test_create_returns_sequence(self, structured_content):
        from src.tools.openhands.game_tool import GameOpenHandsTool

        tools = GameOpenHandsTool.create(structured_content=structured_content)
        assert isinstance(tools, list)
        assert len(tools) == 1
        assert tools[0].name == "game"

    def test_executor_returns_structured_quiz(self, structured_content):
        from openhands.sdk.llm import TextContent

        from src.tools.openhands.game_tool import GameAction, GameOpenHandsTool

        tools = GameOpenHandsTool.create(structured_content=structured_content)
        obs = tools[0].executor(
            GameAction(
                question="What is Python?",
                lesson_id="lesson-test",
                session_id="session-1",
            )
        )

        assert obs.game_type == "multiple_choice"
        assert obs.prompt
        assert len(obs.choices) == 4
        assert isinstance(obs.content, list)
        assert all(isinstance(item, TextContent) for item in obs.content)

    def test_create_fails_without_structured_content(self):
        from src.tools.openhands.game_tool import GameOpenHandsTool

        with pytest.raises(ValueError) as exc_info:
            GameOpenHandsTool.create()
        assert "structured_content" in str(exc_info.value)


# ---------------------------------------------------------------------------
# RetrieveOpenHandsTool Tests
# ---------------------------------------------------------------------------


class TestRetrieveOpenHandsTool:
    """Test RetrieveOpenHandsTool creation, injection, and execution."""

    def test_create_returns_sequence(self, structured_content, lesson_script):
        """Verify create() returns a Sequence of ToolDefinition."""
        from src.tools.openhands.retrieve_tool import RetrieveOpenHandsTool

        tools = RetrieveOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        assert isinstance(tools, list)
        assert len(tools) == 1

    def test_tool_has_required_attributes(self, structured_content, lesson_script):
        """Verify ToolDefinition has required OpenHands attributes."""
        from src.tools.openhands.retrieve_tool import RetrieveOpenHandsTool

        tools = RetrieveOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        tool = tools[0]

        assert tool.name == "retrieve"
        assert hasattr(tool, "action_type")
        assert hasattr(tool, "observation_type")

    def test_error_obs_has_valid_text_content(self, structured_content, lesson_script):
        """Verify error observation has proper TextContent."""
        from src.tools.openhands.retrieve_tool import RetrieveAction, RetrieveOpenHandsTool

        tools = RetrieveOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        executor = tools[0].executor

        # No field provided - should error
        action = RetrieveAction()
        obs = executor(action)

        assert obs.is_error is True
        assert isinstance(obs.content, list)
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in obs.content)
        assert "Error:" in obs.content[0].text

    def test_success_obs_has_valid_text_content(self, structured_content, lesson_script):
        """Verify success observation has LLM-readable content."""
        from src.tools.openhands.retrieve_tool import RetrieveAction, RetrieveOpenHandsTool

        tools = RetrieveOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        executor = tools[0].executor

        action = RetrieveAction(page_id="page-1")
        obs = executor(action)

        # May be error if content not found, but content format should be valid
        assert isinstance(obs.content, list)
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in obs.content)

    def test_create_fails_without_structured_content(self):
        """Verify create() fails explicitly when structured_content is missing."""
        from src.tools.openhands.retrieve_tool import RetrieveOpenHandsTool

        with pytest.raises(ValueError) as exc_info:
            RetrieveOpenHandsTool.create()

        assert "structured_content" in str(exc_info.value)


# ---------------------------------------------------------------------------
# SessionOpenHandsTool Tests
# ---------------------------------------------------------------------------


class TestSessionOpenHandsTool:
    """Test SessionOpenHandsTool creation, injection, and execution."""

    def test_create_returns_sequence(self, session_store):
        """Verify create() returns a Sequence of ToolDefinition."""
        from src.tools.openhands.session_tool import SessionOpenHandsTool

        tools = SessionOpenHandsTool.create(session_store=session_store)
        assert isinstance(tools, list)
        assert len(tools) == 1

    def test_tool_has_required_attributes(self, session_store):
        """Verify ToolDefinition has required OpenHands attributes."""
        from src.tools.openhands.session_tool import SessionOpenHandsTool

        tools = SessionOpenHandsTool.create(session_store=session_store)
        tool = tools[0]

        assert tool.name == "session"
        assert hasattr(tool, "action_type")
        assert hasattr(tool, "observation_type")

    def test_error_obs_has_valid_text_content(self, session_store):
        """Verify error observation has proper TextContent."""
        from src.tools.openhands.session_tool import SessionAction, SessionOpenHandsTool

        tools = SessionOpenHandsTool.create(session_store=session_store)
        executor = tools[0].executor

        action = SessionAction(command="invalid", session_id="test")
        obs = executor(action)

        assert obs.is_error is True
        assert isinstance(obs.content, list)
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in obs.content)
        assert "Error:" in obs.content[0].text

    def test_success_obs_has_valid_text_content(self, session_store, sample_session):
        """Verify success observation has LLM-readable content."""
        from src.tools.openhands.session_tool import SessionAction, SessionOpenHandsTool

        tools = SessionOpenHandsTool.create(session_store=session_store)
        executor = tools[0].executor

        action = SessionAction(command="get", session_id="test-session-001")
        obs = executor(action)

        assert obs.session is not None
        assert isinstance(obs.content, list)
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in obs.content)
        # Content should mention session info
        content_text = obs.content[0].text if obs.content else ""
        assert "Session" in content_text or "session" in content_text

    def test_create_fails_without_session_store(self):
        """Verify create() fails explicitly when session_store is missing."""
        from src.tools.openhands.session_tool import SessionOpenHandsTool

        with pytest.raises(ValueError) as exc_info:
            SessionOpenHandsTool.create()

        assert "session_store" in str(exc_info.value)


# ---------------------------------------------------------------------------
# MemoryOpenHandsTool Tests
# ---------------------------------------------------------------------------


class TestMemoryOpenHandsTool:
    """Test MemoryOpenHandsTool creation, injection, and execution."""

    def test_create_returns_sequence(self, qa_history_store):
        """Verify create() returns a Sequence of ToolDefinition."""
        from src.tools.openhands.memory_tool import MemoryOpenHandsTool

        tools = MemoryOpenHandsTool.create(history_store=qa_history_store)
        assert isinstance(tools, list)
        assert len(tools) == 1

    def test_tool_has_required_attributes(self, qa_history_store):
        """Verify ToolDefinition has required OpenHands attributes."""
        from src.tools.openhands.memory_tool import MemoryOpenHandsTool

        tools = MemoryOpenHandsTool.create(history_store=qa_history_store)
        tool = tools[0]

        assert tool.name == "memory"
        assert hasattr(tool, "action_type")
        assert hasattr(tool, "observation_type")

    def test_error_obs_has_valid_text_content(self, qa_history_store):
        """Verify error observation has proper TextContent."""
        from src.tools.openhands.memory_tool import MemoryAction, MemoryOpenHandsTool

        tools = MemoryOpenHandsTool.create(history_store=qa_history_store)
        executor = tools[0].executor

        action = MemoryAction(command="invalid", session_id="test")
        obs = executor(action)

        assert obs.is_error is True
        assert isinstance(obs.content, list)
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in obs.content)
        assert "Error:" in obs.content[0].text

    def test_add_success_obs_has_valid_text_content(self, qa_history_store):
        """Verify add success observation has LLM-readable content."""
        from src.tools.openhands.memory_tool import MemoryAction, MemoryOpenHandsTool

        tools = MemoryOpenHandsTool.create(history_store=qa_history_store)
        executor = tools[0].executor

        action = MemoryAction(
            command="add",
            session_id="test-session",
            lesson_id="lesson-test",
            question="What is Python?",
            answer="A programming language.",
        )
        obs = executor(action)

        assert obs.total == 1
        assert isinstance(obs.content, list)
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in obs.content)
        assert "added" in obs.content[0].text.lower() or "success" in obs.content[0].text.lower()

    def test_create_fails_without_history_store(self):
        """Verify create() fails explicitly when history_store is missing."""
        from src.tools.openhands.memory_tool import MemoryOpenHandsTool

        with pytest.raises(ValueError) as exc_info:
            MemoryOpenHandsTool.create()

        assert "history_store" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Tool Registration Tests
# ---------------------------------------------------------------------------


class TestToolRegistration:
    """Test that tools are registered correctly in the OpenHands registry."""

    def test_search_tool_is_registered(self):
        """Verify search tool can be resolved from registry."""
        from openhands.sdk.tool.registry import list_registered_tools

        registered = list_registered_tools()
        assert "search" in registered

    def test_retrieve_tool_is_registered(self):
        """Verify retrieve tool can be resolved from registry."""
        from openhands.sdk.tool.registry import list_registered_tools

        registered = list_registered_tools()
        assert "retrieve" in registered

    def test_session_tool_is_registered(self):
        """Verify session tool can be resolved from registry."""
        from openhands.sdk.tool.registry import list_registered_tools

        registered = list_registered_tools()
        assert "session" in registered

    def test_memory_tool_is_registered(self):
        """Verify memory tool can be resolved from registry."""
        from openhands.sdk.tool.registry import list_registered_tools

        registered = list_registered_tools()
        assert "memory" in registered


# ---------------------------------------------------------------------------
# Registry Execution Tests (resolve then execute)
# ---------------------------------------------------------------------------


class TestRegistryExecution:
    """Test that resolved tools can be executed with injected dependencies."""

    def test_resolved_search_executes_successfully(
        self,
        structured_content,
        lesson_script,
    ):
        """Verify search tool resolved from registry can execute with injected deps."""
        from openhands.sdk.tool.registry import resolve_tool
        from openhands.sdk.tool.spec import Tool

        # Create tool spec with params for dependency injection
        tool_spec = Tool(
            name="search",
            params={
                "structured_content": structured_content,
                "lesson_script": lesson_script,
            },
        )

        # Resolve the tool
        tools = resolve_tool(tool_spec, None)
        assert len(tools) == 1
        assert tools[0].name == "search"

        # Execute the tool
        executor = tools[0].executor
        from src.tools.openhands.search_tool import SearchAction

        action = SearchAction(query="Python")
        obs = executor(action)

        # Verify execution was successful
        assert obs.total >= 0
        assert isinstance(obs.content, list)
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in obs.content)

    def test_resolved_retrieve_executes_successfully(
        self,
        structured_content,
        lesson_script,
    ):
        """Verify retrieve tool resolved from registry can execute with injected deps."""
        from openhands.sdk.tool.registry import resolve_tool
        from openhands.sdk.tool.spec import Tool

        tool_spec = Tool(
            name="retrieve",
            params={
                "structured_content": structured_content,
                "lesson_script": lesson_script,
            },
        )

        tools = resolve_tool(tool_spec, None)
        assert len(tools) == 1
        assert tools[0].name == "retrieve"

        executor = tools[0].executor
        from src.tools.openhands.retrieve_tool import RetrieveAction

        action = RetrieveAction(page_id="page-1")
        obs = executor(action)

        # Verify execution was successful
        assert isinstance(obs.content, list)
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in obs.content)

    def test_resolved_session_executes_successfully(self, session_store, sample_session):
        """Verify session tool resolved from registry can execute with injected deps."""
        from openhands.sdk.tool.registry import resolve_tool
        from openhands.sdk.tool.spec import Tool

        tool_spec = Tool(
            name="session",
            params={"session_store": session_store},
        )

        tools = resolve_tool(tool_spec, None)
        assert len(tools) == 1
        assert tools[0].name == "session"

        executor = tools[0].executor
        from src.tools.openhands.session_tool import SessionAction

        action = SessionAction(command="get", session_id="test-session-001")
        obs = executor(action)

        # Verify execution was successful
        assert obs.session is not None
        assert isinstance(obs.content, list)
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in obs.content)

    def test_resolved_memory_executes_successfully(self, qa_history_store):
        """Verify memory tool resolved from registry can execute with injected deps."""
        from openhands.sdk.tool.registry import resolve_tool
        from openhands.sdk.tool.spec import Tool

        tool_spec = Tool(
            name="memory",
            params={"history_store": qa_history_store},
        )

        tools = resolve_tool(tool_spec, None)
        assert len(tools) == 1
        assert tools[0].name == "memory"

        executor = tools[0].executor
        from src.tools.openhands.memory_tool import MemoryAction

        action = MemoryAction(
            command="add",
            session_id="test-session",
            lesson_id="lesson-test",
            question="What is Python?",
            answer="A programming language.",
        )
        obs = executor(action)

        # Verify execution was successful
        assert obs.total == 1
        assert isinstance(obs.content, list)
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in obs.content)

    def test_resolved_search_fails_without_required_deps(self):
        """Verify search tool fails explicitly when required deps are missing via registry."""
        from openhands.sdk.tool.registry import resolve_tool
        from openhands.sdk.tool.spec import Tool

        # Create tool spec WITHOUT required params
        tool_spec = Tool(name="search", params={})

        # Resolve should fail because create() raises ValueError
        with pytest.raises(ValueError) as exc_info:
            resolve_tool(tool_spec, None)

        assert "structured_content" in str(exc_info.value)

    def test_resolved_session_fails_without_required_deps(self):
        """Verify session tool fails explicitly when required deps are missing via registry."""
        from openhands.sdk.tool.registry import resolve_tool
        from openhands.sdk.tool.spec import Tool

        tool_spec = Tool(name="session", params={})

        with pytest.raises(ValueError) as exc_info:
            resolve_tool(tool_spec, None)

        assert "session_store" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Full Integration Tests
# ---------------------------------------------------------------------------


class TestOpenHandsAdapterIntegration:
    """Full integration tests for OpenHands adapters with injected dependencies."""

    def test_search_then_retrieve_chain(
        self,
        structured_content,
        lesson_script,
        session_store,
        qa_history_store,
        sample_session,
    ):
        """Test search -> retrieve chain with injected dependencies."""
        from src.tools.openhands.retrieve_tool import RetrieveAction, RetrieveOpenHandsTool
        from src.tools.openhands.search_tool import SearchAction, SearchOpenHandsTool

        # Create tools with injected dependencies
        search_tools = SearchOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        retrieve_tools = RetrieveOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )

        search_executor = search_tools[0].executor
        retrieve_executor = retrieve_tools[0].executor

        # 1. Search for content
        search_obs = search_executor(SearchAction(query="Python"))
        assert isinstance(search_obs.content, list)
        assert len(search_obs.content) > 0

        # 2. Retrieve specific page
        if search_obs.results:
            first_result = search_obs.results[0]
            retrieve_obs = retrieve_executor(RetrieveAction(page_id=first_result.source_id))
            assert isinstance(retrieve_obs.content, list)
            assert retrieve_obs.retrieved_content is not None

    def test_session_and_memory_with_stores(
        self,
        structured_content,
        lesson_script,
        session_store,
        qa_history_store,
        sample_session,
    ):
        """Test session and memory operations with injected stores."""
        from src.tools.openhands.memory_tool import MemoryAction, MemoryOpenHandsTool
        from src.tools.openhands.session_tool import SessionAction, SessionOpenHandsTool

        # Create tools with injected stores
        session_tools = SessionOpenHandsTool.create(session_store=session_store)
        memory_tools = MemoryOpenHandsTool.create(history_store=qa_history_store)

        session_executor = session_tools[0].executor
        memory_executor = memory_tools[0].executor

        # 1. Get session
        session_obs = session_executor(SessionAction(command="get", session_id="test-session-001"))
        assert isinstance(session_obs.content, list)
        assert session_obs.session is not None

        # 2. Add memory record
        memory_obs = memory_executor(
            MemoryAction(
                command="add",
                session_id="test-session-001",
                lesson_id="lesson-test",
                question="What is Python?",
                answer="A programming language.",
            )
        )
        assert isinstance(memory_obs.content, list)
        assert memory_obs.total == 1

        # 3. Get history
        history_obs = memory_executor(MemoryAction(command="get_history", session_id="test-session-001"))
        assert isinstance(history_obs.content, list)
        assert history_obs.total >= 1
