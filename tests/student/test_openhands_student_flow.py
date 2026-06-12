"""
OpenHands student flow integration tests.

Verifies the OpenHands tool adapters properly integrate with the student workflow:
1. Adapters can be created with injected dependencies
2. Adapters produce valid Observation.content (list of TextContent)
3. Full data collection chain works through adapters
4. Tool registry integration works (resolve + execute)
5. Required dependency enforcement works

Does NOT require:
- Full student/agent.py main entry point
- Actual LLM calls (uses mock LLM)
"""

from __future__ import annotations

import os
import tempfile

import pytest

from src.memory.history import QAHistoryStore
from src.memory.session_store import SessionStore
from src.schemas import (
    LearningSession,
    PageBlock,
    RetrievedContextItem,
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
    """Minimal StructuredLessonContent for integration tests."""
    pages = [
        PageBlock(
            page_id="page-1",
            course_id="course-oh",
            lesson_id="lesson-oh",
            section_id="section-intro",
            page=1,
            title="Introduction to Python",
            content="Python is a high-level programming language. "
            "It supports multiple paradigms including procedural, "
            "object-oriented, and functional programming.",
            summary="Overview of Python language",
            key_points=["high-level", "multi-paradigm", "interpreted"],
            knowledge_points=["Python basics", "programming paradigms"],
            page_role="cover",
        ),
        PageBlock(
            page_id="page-2",
            course_id="course-oh",
            lesson_id="lesson-oh",
            section_id="section-intro",
            page=2,
            title="Python Syntax",
            content="Python uses indentation to define code blocks. "
            "Variables are dynamically typed. "
            "Functions are defined with the 'def' keyword.",
            summary="Basic Python syntax rules",
            key_points=["indentation", "dynamic typing", "def keyword"],
            knowledge_points=["Python syntax", "variables", "functions"],
            page_role="content",
        ),
        PageBlock(
            page_id="page-3",
            course_id="course-oh",
            lesson_id="lesson-oh",
            section_id="section-advanced",
            page=3,
            title="Advanced Python",
            content="Advanced topics include decorators, generators, "
            "context managers, and metaclasses. "
            "These features enable powerful abstraction patterns.",
            summary="Advanced Python features",
            key_points=["decorators", "generators", "metaclasses"],
            knowledge_points=["Python advanced features"],
            page_role="content",
        ),
    ]
    sections = [
        SectionBlock(
            section_id="section-intro",
            course_id="course-oh",
            lesson_id="lesson-oh",
            name="Python Basics",
            summary="Introduction to Python programming",
            page_range=[1, 2],
            key_points=["syntax", "variables", "functions"],
            knowledge_points=["Python basics"],
            section_type="intro",
        ),
        SectionBlock(
            section_id="section-advanced",
            course_id="course-oh",
            lesson_id="lesson-oh",
            name="Advanced Python",
            summary="Advanced Python features",
            page_range=[3],
            key_points=["decorators", "generators"],
            knowledge_points=["Python advanced"],
            section_type="content",
        ),
    ]
    return StructuredLessonContent(
        course_id="course-oh",
        lesson_id="lesson-oh",
        source_asset_ids=["asset-1"],
        lesson_summary="A Python programming lesson covering basics and advanced topics.",
        pages=pages,
        sections=sections,
        knowledge_points=["Python basics", "Python advanced features"],
    )


@pytest.fixture
def lesson_script():
    """Minimal LessonScript for integration tests."""
    blocks = [
        ScriptBlock(
            script_block_id="block-opening",
            course_id="course-oh",
            lesson_id="lesson-oh",
            section_id="section-intro",
            title="Lesson Opening",
            script_text="Welcome to this Python lesson. Today we will learn "
            "about Python syntax, variables, and functions.",
            key_points=["welcome", "overview"],
            block_type="opening",
            page_range=[1],
        ),
        ScriptBlock(
            script_block_id="block-teaching-1",
            course_id="course-oh",
            lesson_id="lesson-oh",
            section_id="section-intro",
            title="Teaching Section 1",
            script_text="Python is a high-level language that is easy to read. "
            "Let me show you the basic syntax.",
            key_points=["high-level", "readable"],
            block_type="teaching",
            page_range=[1, 2],
        ),
        ScriptBlock(
            script_block_id="block-advanced",
            course_id="course-oh",
            lesson_id="lesson-oh",
            section_id="section-advanced",
            title="Advanced Features",
            script_text="Now let's discuss decorators and generators. These are powerful features of Python.",
            key_points=["decorators", "generators"],
            block_type="teaching",
            page_range=[3],
        ),
    ]
    return LessonScript(
        lesson_title="Python Programming Lesson",
        script_blocks=blocks,
        metadata={"lesson_id": "lesson-oh"},
    )


# ---------------------------------------------------------------------------
# Store fixtures (isolated temp DBs)
# ---------------------------------------------------------------------------


@pytest.fixture
def session_store():
    """Temp SessionStore for integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_sessions_oh.db")
        yield SessionStore(db_path=db_path)


@pytest.fixture
def qa_history_store():
    """Temp QAHistoryStore for integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_qa_history_oh.db")
        yield QAHistoryStore(db_path=db_path)


# ---------------------------------------------------------------------------
# Session fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_session(session_store):
    """Create and persist a LearningSession for integration tests."""
    session = LearningSession(
        session_id="oh-session-001",
        course_id="course-oh",
        lesson_id="lesson-oh",
        user_id="student-001",
        status="active",
        current_section_id="section-intro",
        current_page=1,
        current_script_block_id="block-opening",
        progress_percent=0.0,
    )
    return session_store.save(session)


# ---------------------------------------------------------------------------
# OpenHands Adapter Creation Tests
# ---------------------------------------------------------------------------


class TestOpenHandsAdapterCreation:
    """Verify OpenHands tool adapters can be created with proper dependencies."""

    def test_search_adapter_with_full_context(
        self,
        structured_content,
        lesson_script,
    ):
        """SearchOpenHandsTool can be created with structured_content and lesson_script."""
        from src.tools.openhands.search_tool import SearchOpenHandsTool

        tools = SearchOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        assert len(tools) == 1
        assert tools[0].name == "search"
        assert tools[0].executor is not None

    def test_retrieve_adapter_with_full_context(
        self,
        structured_content,
        lesson_script,
    ):
        """RetrieveOpenHandsTool can be created with structured_content and lesson_script."""
        from src.tools.openhands.retrieve_tool import RetrieveOpenHandsTool

        tools = RetrieveOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        assert len(tools) == 1
        assert tools[0].name == "retrieve"
        assert tools[0].executor is not None

    def test_session_adapter_with_store(self, session_store):
        """SessionOpenHandsTool can be created with session_store."""
        from src.tools.openhands.session_tool import SessionOpenHandsTool

        tools = SessionOpenHandsTool.create(session_store=session_store)
        assert len(tools) == 1
        assert tools[0].name == "session"
        assert tools[0].executor is not None

    def test_memory_adapter_with_store(self, qa_history_store):
        """MemoryOpenHandsTool can be created with history_store."""
        from src.tools.openhands.memory_tool import MemoryOpenHandsTool

        tools = MemoryOpenHandsTool.create(history_store=qa_history_store)
        assert len(tools) == 1
        assert tools[0].name == "memory"
        assert tools[0].executor is not None


# ---------------------------------------------------------------------------
# OpenHands Adapter Execution Tests
# ---------------------------------------------------------------------------


class TestOpenHandsAdapterExecution:
    """Verify OpenHands tool adapters execute properly and return valid observations."""

    def test_search_execution_returns_content(
        self,
        structured_content,
        lesson_script,
    ):
        """Search adapter returns valid content list for LLM."""
        from src.tools.openhands.search_tool import SearchAction, SearchOpenHandsTool

        tools = SearchOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        executor = tools[0].executor

        action = SearchAction(query="high-level programming language")
        obs = executor(action)

        # Must have valid content list
        assert isinstance(obs.content, list)
        assert len(obs.content) > 0
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in obs.content)
        # Content must be readable
        content_text = obs.content[0].text
        assert len(content_text) > 0

    def test_retrieve_execution_returns_content(
        self,
        structured_content,
        lesson_script,
    ):
        """Retrieve adapter returns valid content list for LLM."""
        from src.tools.openhands.retrieve_tool import RetrieveAction, RetrieveOpenHandsTool

        tools = RetrieveOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        executor = tools[0].executor

        action = RetrieveAction(page_id="page-1")
        obs = executor(action)

        # Must have valid content list
        assert isinstance(obs.content, list)
        assert len(obs.content) > 0
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in obs.content)
        # Content must mention the page title
        content_text = obs.content[0].text
        assert "Introduction to Python" in content_text or "Python" in content_text

    def test_session_execution_returns_content(self, session_store, sample_session):
        """Session adapter returns valid content list for LLM."""
        from src.tools.openhands.session_tool import SessionAction, SessionOpenHandsTool

        tools = SessionOpenHandsTool.create(session_store=session_store)
        executor = tools[0].executor

        action = SessionAction(command="get", session_id="oh-session-001")
        obs = executor(action)

        # Must have valid content list
        assert isinstance(obs.content, list)
        assert len(obs.content) > 0
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in obs.content)
        # Content must mention session info
        content_text = obs.content[0].text
        assert "oh-session-001" in content_text or "Session" in content_text

    def test_memory_execution_returns_content(self, qa_history_store):
        """Memory adapter returns valid content list for LLM."""
        from src.tools.openhands.memory_tool import MemoryAction, MemoryOpenHandsTool

        tools = MemoryOpenHandsTool.create(history_store=qa_history_store)
        executor = tools[0].executor

        action = MemoryAction(
            command="add",
            session_id="oh-session-001",
            lesson_id="lesson-oh",
            question="What is Python?",
            answer="A programming language.",
        )
        obs = executor(action)

        # Must have valid content list
        assert isinstance(obs.content, list)
        assert len(obs.content) > 0
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in obs.content)
        # Content must mention success
        content_text = obs.content[0].text
        assert "added" in content_text.lower() or "success" in content_text.lower()


# ---------------------------------------------------------------------------
# Full Student Flow Through OpenHands Adapters
# ---------------------------------------------------------------------------


class TestOpenHandsStudentFlow:
    """Test complete student data collection flow through OpenHands adapters."""

    def test_search_retrieve_memory_session_chain(
        self,
        structured_content,
        lesson_script,
        session_store,
        qa_history_store,
        sample_session,
    ):
        """
        Full flow: search -> retrieve -> memory add -> session update.
        All through OpenHands adapters with proper dependency injection.
        """
        from src.tools.openhands.memory_tool import MemoryAction, MemoryOpenHandsTool
        from src.tools.openhands.retrieve_tool import RetrieveAction, RetrieveOpenHandsTool
        from src.tools.openhands.search_tool import SearchAction, SearchOpenHandsTool
        from src.tools.openhands.session_tool import SessionAction, SessionOpenHandsTool

        # Create all adapters with injected dependencies
        search_tools = SearchOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        retrieve_tools = RetrieveOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        session_tools = SessionOpenHandsTool.create(session_store=session_store)
        memory_tools = MemoryOpenHandsTool.create(history_store=qa_history_store)

        search_executor = search_tools[0].executor
        retrieve_executor = retrieve_tools[0].executor
        session_executor = session_tools[0].executor
        memory_executor = memory_tools[0].executor

        # 1. Search for content
        search_obs = search_executor(SearchAction(query="high-level programming language"))
        assert search_obs.total >= 1
        assert isinstance(search_obs.content, list)
        from openhands.sdk.llm import TextContent

        assert all(isinstance(c, TextContent) for c in search_obs.content)

        # 2. Retrieve the specific page content
        first_result = search_obs.results[0]
        retrieve_obs = retrieve_executor(RetrieveAction(page_id=first_result.source_id))
        assert retrieve_obs.source == "page"
        assert isinstance(retrieve_obs.content, list)
        assert len(retrieve_obs.content[0].text) > 0

        # 3. Add Q&A record to memory
        memory_obs = memory_executor(
            MemoryAction(
                command="add",
                session_id="oh-session-001",
                lesson_id="lesson-oh",
                question="What is a high-level programming language?",
                answer=retrieve_obs.retrieved_content.get("text", ""),
                references=[
                    {
                        "source_type": "lesson",
                        "source_name": retrieve_obs.retrieved_content.get("title", ""),
                        "snippet": retrieve_obs.retrieved_content.get("text", "")[:100],
                        "page": retrieve_obs.retrieved_content.get("page"),
                    }
                ],
            )
        )
        assert memory_obs.total == 1
        assert isinstance(memory_obs.content, list)

        # 4. Update session progress
        session_obs = session_executor(
            SessionAction(
                command="update",
                session_id="oh-session-001",
                progress_percent=33.3,
                section_id="section-intro",
                page=2,
            )
        )
        assert session_obs.session is not None
        assert session_obs.session.progress_percent == 33.3
        assert isinstance(session_obs.content, list)

        # 5. Verify memory and session state
        history_obs = memory_executor(MemoryAction(command="get_history", session_id="oh-session-001"))
        assert history_obs.total == 1
        assert isinstance(history_obs.content, list)

        session_final_obs = session_executor(SessionAction(command="get", session_id="oh-session-001"))
        assert session_final_obs.session.progress_percent == 33.3
        assert isinstance(session_final_obs.content, list)

    def test_flow_with_section_filter_and_script_retrieval(
        self,
        structured_content,
        lesson_script,
        session_store,
        qa_history_store,
        sample_session,
    ):
        """Flow with section filter targeting advanced section and script retrieval."""
        from src.tools.openhands.memory_tool import MemoryAction, MemoryOpenHandsTool
        from src.tools.openhands.retrieve_tool import RetrieveAction, RetrieveOpenHandsTool
        from src.tools.openhands.search_tool import SearchAction, SearchOpenHandsTool
        from src.tools.openhands.session_tool import SessionAction, SessionOpenHandsTool

        search_tools = SearchOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        retrieve_tools = RetrieveOpenHandsTool.create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        session_tools = SessionOpenHandsTool.create(session_store=session_store)
        memory_tools = MemoryOpenHandsTool.create(history_store=qa_history_store)

        search_executor = search_tools[0].executor
        retrieve_executor = retrieve_tools[0].executor
        session_executor = session_tools[0].executor
        memory_executor = memory_tools[0].executor

        # 1. Search with section filter
        search_obs = search_executor(
            SearchAction(
                query="decorators generators",
                section_filter="section-advanced",
                include_script=True,
            )
        )
        assert search_obs.total >= 1
        assert all(r.section_id == "section-advanced" for r in search_obs.results)

        # 2. Retrieve script block if found
        script_result = next((r for r in search_obs.results if r.source == "script_block"), None)
        if script_result:
            retrieve_obs = retrieve_executor(RetrieveAction(script_block_id=script_result.source_id))
            assert retrieve_obs.source == "script_block"
            assert isinstance(retrieve_obs.content, list)

        # 3. Record interaction in memory
        answer_text = retrieve_obs.retrieved_content.get("text", "") if script_result else "No script found"
        memory_obs = memory_executor(
            MemoryAction(
                command="add",
                session_id="oh-session-001",
                lesson_id="lesson-oh",
                question="Explain decorators and generators.",
                answer=answer_text,
            )
        )
        assert memory_obs.total >= 1

        # 4. Update session position
        session_obs = session_executor(
            SessionAction(
                command="update",
                session_id="oh-session-001",
                section_id="section-advanced",
                page=3,
                progress_percent=75.0,
            )
        )
        assert session_obs.session.current_section_id == "section-advanced"


# ---------------------------------------------------------------------------
# Tool Registry Integration Tests (resolve + execute)
# ---------------------------------------------------------------------------


class TestToolRegistryIntegration:
    """
    Verify tools can be resolved from the OpenHands registry and executed.
    These tests ensure the full resolve -> execute pipeline works.
    """

    def test_resolve_and_execute_search(
        self,
        structured_content,
        lesson_script,
    ):
        """Search tool resolved from registry executes successfully with injected deps."""
        from openhands.sdk.tool.registry import resolve_tool
        from openhands.sdk.tool.spec import Tool

        from src.tools.openhands.search_tool import SearchAction

        tool_spec = Tool(
            name="search",
            params={
                "structured_content": structured_content,
                "lesson_script": lesson_script,
            },
        )

        tools = resolve_tool(tool_spec, None)
        assert len(tools) == 1
        assert tools[0].name == "search"

        # Execute
        obs = tools[0].executor(SearchAction(query="Python"))
        assert obs.total >= 0
        assert isinstance(obs.content, list)

    def test_resolve_and_execute_retrieve(
        self,
        structured_content,
        lesson_script,
    ):
        """Retrieve tool resolved from registry executes successfully with injected deps."""
        from openhands.sdk.tool.registry import resolve_tool
        from openhands.sdk.tool.spec import Tool

        from src.tools.openhands.retrieve_tool import RetrieveAction

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

        # Execute
        obs = tools[0].executor(RetrieveAction(page_id="page-1"))
        assert isinstance(obs.content, list)

    def test_resolve_and_execute_session(self, session_store, sample_session):
        """Session tool resolved from registry executes successfully with injected deps."""
        from openhands.sdk.tool.registry import resolve_tool
        from openhands.sdk.tool.spec import Tool

        from src.tools.openhands.session_tool import SessionAction

        tool_spec = Tool(
            name="session",
            params={"session_store": session_store},
        )

        tools = resolve_tool(tool_spec, None)
        assert len(tools) == 1
        assert tools[0].name == "session"

        # Execute
        obs = tools[0].executor(SessionAction(command="get", session_id="oh-session-001"))
        assert obs.session is not None
        assert obs.session.session_id == "oh-session-001"
        assert isinstance(obs.content, list)

    def test_resolve_and_execute_memory(self, qa_history_store):
        """Memory tool resolved from registry executes successfully with injected deps."""
        from openhands.sdk.tool.registry import resolve_tool
        from openhands.sdk.tool.spec import Tool

        from src.tools.openhands.memory_tool import MemoryAction

        tool_spec = Tool(
            name="memory",
            params={"history_store": qa_history_store},
        )

        tools = resolve_tool(tool_spec, None)
        assert len(tools) == 1
        assert tools[0].name == "memory"

        # Execute
        obs = tools[0].executor(
            MemoryAction(
                command="add",
                session_id="oh-session-001",
                lesson_id="lesson-oh",
                question="Test question?",
                answer="Test answer.",
            )
        )
        assert obs.total == 1
        assert isinstance(obs.content, list)


# ---------------------------------------------------------------------------
# Negative Tests: Missing Dependencies
# ---------------------------------------------------------------------------


class TestMissingDependencyEnforcement:
    """
    Verify that tools fail explicitly when required dependencies are missing.
    No silent fallback to default behavior.
    """

    def test_search_fails_without_structured_content(self):
        """Search adapter fails explicitly when structured_content is missing."""
        from src.tools.openhands.search_tool import SearchOpenHandsTool

        with pytest.raises(ValueError) as exc_info:
            SearchOpenHandsTool.create()

        assert "structured_content" in str(exc_info.value)

    def test_retrieve_fails_without_structured_content(self):
        """Retrieve adapter fails explicitly when structured_content is missing."""
        from src.tools.openhands.retrieve_tool import RetrieveOpenHandsTool

        with pytest.raises(ValueError) as exc_info:
            RetrieveOpenHandsTool.create()

        assert "structured_content" in str(exc_info.value)

    def test_session_fails_without_session_store(self):
        """Session adapter fails explicitly when session_store is missing."""
        from src.tools.openhands.session_tool import SessionOpenHandsTool

        with pytest.raises(ValueError) as exc_info:
            SessionOpenHandsTool.create()

        assert "session_store" in str(exc_info.value)

    def test_memory_fails_without_history_store(self):
        """Memory adapter fails explicitly when history_store is missing."""
        from src.tools.openhands.memory_tool import MemoryOpenHandsTool

        with pytest.raises(ValueError) as exc_info:
            MemoryOpenHandsTool.create()

        assert "history_store" in str(exc_info.value)

    def test_registry_resolve_fails_search_without_deps(self):
        """Registry resolve fails for search when required deps not in params."""
        from openhands.sdk.tool.registry import resolve_tool
        from openhands.sdk.tool.spec import Tool

        tool_spec = Tool(name="search", params={})

        with pytest.raises(ValueError) as exc_info:
            resolve_tool(tool_spec, None)

        assert "structured_content" in str(exc_info.value)

    def test_registry_resolve_fails_session_without_deps(self):
        """Registry resolve fails for session when required deps not in params."""
        from openhands.sdk.tool.registry import resolve_tool
        from openhands.sdk.tool.spec import Tool

        tool_spec = Tool(name="session", params={})

        with pytest.raises(ValueError) as exc_info:
            resolve_tool(tool_spec, None)

        assert "session_store" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Regression Baseline: Old Tool Tests (kept for comparison)
# ---------------------------------------------------------------------------


class TestOldToolRegressionBaseline:
    """
    Regression baseline for old business tools.
    These tests verify the underlying business tools still work correctly.
    Kept as a baseline to ensure adapters don't break underlying functionality.
    """

    def test_old_search_tool_still_works(self, structured_content, lesson_script):
        """Regression: SearchTool must still return valid results."""
        from src.tools.search import SearchAction, SearchTool
        from src.utils.student import HybridRetriever

        retriever = HybridRetriever(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        tool = SearchTool(retriever)
        action = SearchAction(query="Python syntax")
        obs = tool.search(action)

        assert obs.total >= 1
        assert all(isinstance(r, RetrievedContextItem) for r in obs.results)

    def test_old_retrieve_tool_still_works(self, structured_content, lesson_script):
        """Regression: RetrieveTool must still return valid content."""
        from src.tools.retrieve import RetrieveAction, RetrieveTool
        from src.utils.student import ContentGetter

        content_getter = ContentGetter(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        tool = RetrieveTool(content_getter)
        action = RetrieveAction(page_id="page-1")
        obs = tool.retrieve(action)

        assert obs.source == "page"
        assert "text" in obs.content

    def test_old_session_tool_still_works(self, session_store, sample_session):
        """Regression: SessionTool update must be visible in get."""
        from src.tools.session import SessionAction, SessionTool

        tool = SessionTool(session_store=session_store)
        tool.execute(
            SessionAction(
                command="update",
                session_id="oh-session-001",
                progress_percent=66.6,
            )
        )
        obs = tool.execute(
            SessionAction(
                command="get",
                session_id="oh-session-001",
            )
        )
        assert obs.session.progress_percent == 66.6

    def test_old_memory_tool_still_works(self, qa_history_store):
        """Regression: MemoryTool add must be searchable."""
        from src.tools.memory import MemoryTool

        tool = MemoryTool(store=qa_history_store)
        tool.run(
            {
                "command": "add",
                "session_id": "oh-session-001",
                "lesson_id": "lesson-oh",
                "question": "What are decorators?",
                "answer": "Decorators are functions that modify other functions.",
            }
        )
        result = tool.run(
            {
                "command": "search",
                "session_id": "oh-session-001",
                "keyword": "decorator",
            }
        )
        assert result["total"] >= 1


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

"""
Test Summary:
- test_openhands_student_flow.py now covers:
  1. OpenHands adapter creation with dependency injection
  2. Adapter execution returning valid Observation.content (list of TextContent)
  3. Full student flow data collection chain through adapters
  4. Tool registry resolution + execution (not just name checks)
  5. Negative tests for missing required dependencies
  6. Regression baseline for old business tools

What is NOT covered (requires full agent main entry):
  - Actual LLM-powered agent run
  - Full StudentAgentResponse generation
  - OpenHands agent + tool adapter end-to-end run
  - QA/decision stages through OpenHands

Key validation points:
  - Adapters properly accept injected dependencies
  - Adapters return valid LLM-readable content
  - Tool chain works end-to-end through adapters
  - Registry resolve + execute pipeline works
  - Missing required dependencies fail explicitly
  - Underlying business tools still work (regression baseline)
"""
