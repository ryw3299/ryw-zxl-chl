"""
Tools layer integration tests.

Verifies SearchTool, RetrieveTool, SessionTool, and MemoryTool can work
together on the same structured_content / lesson_script / session / history data.

No business logic is changed; only test scaffolding is added.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from src.memory.history import QAHistoryStore
from src.memory.session_store import SessionStore
from src.schemas.common import (
    LearningSession,
    PageBlock,
    ScriptBlock,
    SectionBlock,
    StructuredLessonContent,
)
from src.schemas.generate_schemas import LessonScript
from src.tools.memory import MemoryTool
from src.tools.retrieve import RetrieveAction, RetrieveTool
from src.tools.search import SearchAction, SearchTool
from src.tools.session import SessionAction, SessionTool
from src.utils.student import ContentGetter, HybridRetriever

# ---------------------------------------------------------------------------
# Shared test data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def structured_content():
    """Minimal StructuredLessonContent for integration tests."""
    pages = [
        PageBlock(
            page_id="page-1",
            course_id="course-integration",
            lesson_id="lesson-integration",
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
            course_id="course-integration",
            lesson_id="lesson-integration",
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
            course_id="course-integration",
            lesson_id="lesson-integration",
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
            course_id="course-integration",
            lesson_id="lesson-integration",
            name="Python Basics",
            summary="Introduction to Python programming",
            page_range=[1, 2],
            key_points=["syntax", "variables", "functions"],
            knowledge_points=["Python basics"],
            section_type="intro",
        ),
        SectionBlock(
            section_id="section-advanced",
            course_id="course-integration",
            lesson_id="lesson-integration",
            name="Advanced Python",
            summary="Advanced Python features",
            page_range=[3],
            key_points=["decorators", "generators"],
            knowledge_points=["Python advanced"],
            section_type="content",
        ),
    ]
    return StructuredLessonContent(
        course_id="course-integration",
        lesson_id="lesson-integration",
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
            course_id="course-integration",
            lesson_id="lesson-integration",
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
            course_id="course-integration",
            lesson_id="lesson-integration",
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
            course_id="course-integration",
            lesson_id="lesson-integration",
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
        metadata={"lesson_id": "lesson-integration"},
    )


# ---------------------------------------------------------------------------
# Store fixtures (each test gets isolated temp DBs)
# ---------------------------------------------------------------------------


@pytest.fixture
def session_store():
    """Temp SessionStore for integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_sessions.db")
        store = SessionStore(db_path=db_path)
        yield store


@pytest.fixture
def qa_history_store():
    """Temp QAHistoryStore for integration tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_qa_history.db")
        store = QAHistoryStore(db_path=db_path)
        yield store


# ---------------------------------------------------------------------------
# Tool fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def search_tool(structured_content, lesson_script):
    """SearchTool wired to real HybridRetriever on shared test data."""
    retriever = HybridRetriever(
        structured_content=structured_content,
        lesson_script=lesson_script,
    )
    return SearchTool(retriever)


@pytest.fixture
def retrieve_tool(structured_content, lesson_script):
    """RetrieveTool wired to real ContentGetter on shared test data."""
    content_getter = ContentGetter(
        structured_content=structured_content,
        lesson_script=lesson_script,
    )
    return RetrieveTool(content_getter)


@pytest.fixture
def session_tool(session_store):
    """SessionTool wired to isolated temp SessionStore."""
    return SessionTool(session_store=session_store)


@pytest.fixture
def memory_tool(qa_history_store):
    """MemoryTool wired to isolated temp QAHistoryStore."""
    return MemoryTool(store=qa_history_store)


# ---------------------------------------------------------------------------
# Session fixture (pre-populated in the temp session store)
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_session(session_store):
    """Create and persist a LearningSession for integration tests."""
    session = LearningSession(
        session_id="integration-session-001",
        course_id="course-integration",
        lesson_id="lesson-integration",
        user_id="student-001",
        status="active",
        current_section_id="section-intro",
        current_page=1,
        current_script_block_id="block-opening",
        progress_percent=0.0,
    )
    return session_store.save(session)


# ---------------------------------------------------------------------------
# Tests: individual tool verification on shared data
# ---------------------------------------------------------------------------


class TestSearchToolIntegration:
    """Verify SearchTool returns RetrievedContextItem list on real HybridRetriever."""

    def test_search_returns_results(self, search_tool):
        """SearchTool.query returns non-empty results for a known term."""
        action = SearchAction(query="Python syntax")
        obs = search_tool.search(action)

        assert isinstance(obs.results, list)
        assert obs.total >= 1
        assert all(r.source in ("page", "section", "script_block") for r in obs.results)

    def test_search_page_filter(self, search_tool):
        """SearchTool respects page_filter."""
        action = SearchAction(query="Python", page_filter=2)
        obs = search_tool.search(action)

        assert all(r.page == 2 for r in obs.results)

    def test_search_section_filter(self, search_tool):
        """SearchTool respects section_filter."""
        action = SearchAction(query="decorators", section_filter="section-advanced")
        obs = search_tool.search(action)

        assert all(r.section_id == "section-advanced" for r in obs.results)

    def test_search_exclude_script(self, search_tool):
        """SearchTool.include_script=False excludes script_block results."""
        action = SearchAction(query="Python", include_script=False)
        obs = search_tool.search(action)

        assert all(r.source != "script_block" for r in obs.results)


class TestRetrieveToolIntegration:
    """Verify RetrieveTool can fetch exact page/section/script_block by ID."""

    def test_retrieve_page_by_id(self, retrieve_tool):
        """RetrieveTool returns correct page content."""
        action = RetrieveAction(page_id="page-1")
        obs = retrieve_tool.retrieve(action)

        assert obs.source == "page"
        assert obs.content["source_id"] == "page-1"
        assert "Python" in obs.content["text"]

    def test_retrieve_section_by_id(self, retrieve_tool):
        """RetrieveTool returns correct section content."""
        action = RetrieveAction(section_id="section-intro")
        obs = retrieve_tool.retrieve(action)

        assert obs.source == "section"
        assert obs.content["source_id"] == "section-intro"
        assert obs.content["title"] == "Python Basics"

    def test_retrieve_script_block_by_id(self, retrieve_tool):
        """RetrieveTool returns correct script block content."""
        action = RetrieveAction(script_block_id="block-teaching-1")
        obs = retrieve_tool.retrieve(action)

        assert obs.source == "script_block"
        assert obs.content["source_id"] == "block-teaching-1"
        assert "Python" in obs.content["text"]

    def test_retrieve_by_page_number(self, retrieve_tool):
        """RetrieveTool can look up page by 1-based page number."""
        action = RetrieveAction(page=2)
        obs = retrieve_tool.retrieve(action)

        assert obs.source == "page"
        assert obs.content["page"] == 2


class TestSessionToolIntegration:
    """Verify SessionTool can get and update the same session."""

    def test_session_get_existing(self, session_tool, sample_session):
        """SessionTool.get returns the pre-populated session."""
        obs = session_tool.execute(
            SessionAction(
                command="get",
                session_id="integration-session-001",
            )
        )

        assert obs.session is not None
        assert obs.session.session_id == "integration-session-001"
        assert obs.session.lesson_id == "lesson-integration"

    def test_session_update_progress(self, session_tool, sample_session):
        """SessionTool.update can advance progress_percent."""
        obs = session_tool.execute(
            SessionAction(
                command="update",
                session_id="integration-session-001",
                progress_percent=33.3,
            )
        )

        assert obs.session is not None
        assert obs.session.progress_percent == 33.3

    def test_session_update_position(self, session_tool, sample_session):
        """SessionTool.update can move to a different section/page."""
        obs = session_tool.execute(
            SessionAction(
                command="update",
                session_id="integration-session-001",
                section_id="section-advanced",
                page=3,
                script_block_id="block-advanced",
            )
        )

        assert obs.session is not None
        assert obs.session.current_section_id == "section-advanced"
        assert obs.session.current_page == 3
        assert obs.session.current_script_block_id == "block-advanced"

    def test_session_get_after_update_returns_updated(self, session_tool, sample_session):
        """After an update, a subsequent get reflects the new state."""
        session_tool.execute(
            SessionAction(
                command="update",
                session_id="integration-session-001",
                progress_percent=75.0,
            )
        )

        obs = session_tool.execute(
            SessionAction(
                command="get",
                session_id="integration-session-001",
            )
        )

        assert obs.session.progress_percent == 75.0


class TestMemoryToolIntegration:
    """Verify MemoryTool can add records and retrieve them within the same session."""

    def test_memory_add_and_get_history(self, memory_tool):
        """MemoryTool can add a record and retrieve it via get_history."""
        memory_tool.run(
            {
                "command": "add",
                "session_id": "integration-session-001",
                "lesson_id": "lesson-integration",
                "question": "What is Python?",
                "answer": "A high-level programming language.",
            }
        )

        result = memory_tool.run(
            {
                "command": "get_history",
                "session_id": "integration-session-001",
            }
        )

        assert result["total"] == 1
        assert result["records"][0]["question"] == "What is Python?"

    def test_memory_search(self, memory_tool):
        """MemoryTool can search records by keyword."""
        memory_tool.run(
            {
                "command": "add",
                "session_id": "integration-session-001",
                "lesson_id": "lesson-integration",
                "question": "What are decorators?",
                "answer": "Decorators are functions that modify other functions.",
            }
        )
        memory_tool.run(
            {
                "command": "add",
                "session_id": "integration-session-001",
                "lesson_id": "lesson-integration",
                "question": "What are generators?",
                "answer": "Generators are iterators that yield values.",
            }
        )

        result = memory_tool.run(
            {
                "command": "search",
                "keyword": "decorator",
            }
        )

        assert result["total"] == 1
        assert "decorator" in result["records"][0]["question"].lower()

    def test_memory_get_history_empty_for_unknown_session(self, memory_tool):
        """MemoryTool.get_history returns empty for a session with no records."""
        result = memory_tool.run(
            {
                "command": "get_history",
                "session_id": "nonexistent-session",
            }
        )

        assert result["records"] == []
        assert result["total"] == 0

    def test_memory_add_with_references(self, memory_tool):
        """MemoryTool.add can store references."""
        result = memory_tool.run(
            {
                "command": "add",
                "session_id": "integration-session-001",
                "lesson_id": "lesson-integration",
                "question": "Explain indentation in Python.",
                "answer": "Python uses indentation to define code blocks.",
                "references": [
                    {"source_type": "lesson", "snippet": "Python uses indentation..."},
                    {"source_type": "script", "snippet": "Indentation matters..."},
                ],
            }
        )

        assert result["total"] == 1
        assert len(result["records"][0]["references"]) == 2


# ---------------------------------------------------------------------------
# Tests: combined chain (search -> retrieve -> memory add -> session update)
# ---------------------------------------------------------------------------


class TestToolsChain:
    """
    End-to-end chain: search -> retrieve -> memory add -> session update.

    Simulates a student turn:
      1. Student asks "What is Python?"
      2. SearchTool finds relevant context
      3. RetrieveTool fetches the exact page content
      4. MemoryTool records the Q&A
      5. SessionTool updates progress after the interaction
    """

    def test_full_chain_search_retrieve_memory_session(
        self,
        search_tool,
        retrieve_tool,
        memory_tool,
        session_tool,
        sample_session,
    ):
        # 1. Search for content related to the student's question
        search_obs = search_tool.search(SearchAction(query="high-level programming language"))
        assert search_obs.total >= 1

        # 2. Retrieve the specific page that was found
        first_result = search_obs.results[0]
        retrieve_obs = retrieve_tool.retrieve(RetrieveAction(page_id=first_result.source_id))
        assert retrieve_obs.source == "page"
        assert len(retrieve_obs.content["text"]) > 0

        # 3. Add the Q&A record to memory with retrieved content as reference
        memory_result = memory_tool.run(
            {
                "command": "add",
                "session_id": "integration-session-001",
                "lesson_id": "lesson-integration",
                "question": "What is a high-level programming language?",
                "answer": retrieve_obs.content["text"],
                "references": [
                    {
                        "source_type": "lesson",
                        "source_name": retrieve_obs.content["title"],
                        "snippet": retrieve_obs.content["text"][:100],
                        "page": retrieve_obs.content.get("page"),
                    }
                ],
            }
        )
        assert memory_result["total"] == 1
        assert "high-level" in memory_result["records"][0]["answer"]

        # 4. Update session progress after answering
        session_obs = session_tool.execute(
            SessionAction(
                command="update",
                session_id="integration-session-001",
                progress_percent=50.0,
                section_id="section-intro",
                page=2,
            )
        )
        assert session_obs.session is not None
        assert session_obs.session.progress_percent == 50.0

        # 5. Verify memory and session state is consistent
        history = memory_tool.run(
            {
                "command": "get_history",
                "session_id": "integration-session-001",
            }
        )
        assert history["total"] == 1
        assert history["records"][0]["question"] == "What is a high-level programming language?"

        session_final = session_tool.execute(
            SessionAction(
                command="get",
                session_id="integration-session-001",
            )
        )
        assert session_final.session.progress_percent == 50.0

    def test_chain_with_section_filter_and_script_retrieval(
        self,
        search_tool,
        retrieve_tool,
        memory_tool,
        session_tool,
        sample_session,
    ):
        """Chain using section_filter to target script_block retrieval."""
        # 1. Search with section filter targeting the advanced section
        search_obs = search_tool.search(
            SearchAction(
                query="decorators generators",
                section_filter="section-advanced",
                include_script=True,
            )
        )
        assert search_obs.total >= 1

        # 2. Retrieve the specific script block from results
        script_result = next(r for r in search_obs.results if r.source == "script_block")
        retrieve_obs = retrieve_tool.retrieve(RetrieveAction(script_block_id=script_result.source_id))
        assert retrieve_obs.source == "script_block"

        # 3. Record the interaction in memory
        memory_tool.run(
            {
                "command": "add",
                "session_id": "integration-session-001",
                "lesson_id": "lesson-integration",
                "question": "Explain decorators and generators.",
                "answer": retrieve_obs.content["text"],
            }
        )

        # 4. Update session to reflect position in advanced section
        session_obs = session_tool.execute(
            SessionAction(
                command="update",
                session_id="integration-session-001",
                section_id="section-advanced",
                page=3,
                script_block_id=script_result.source_id,
                progress_percent=80.0,
            )
        )
        assert session_obs.session.current_section_id == "section-advanced"
        assert session_obs.session.progress_percent == 80.0

        # 5. Verify search can find the new memory record
        search_memory = memory_tool.run(
            {
                "command": "search",
                "keyword": "decorator",
            }
        )
        assert search_memory["total"] == 1

    def test_retrieve_then_update_then_search_memory(
        self,
        retrieve_tool,
        session_tool,
        memory_tool,
        sample_session,
    ):
        """
        Retrieve exact content, update session position, then record a new QA pair.
        """
        # 1. Retrieve a section directly
        retrieve_obs = retrieve_tool.retrieve(RetrieveAction(section_id="section-intro"))
        assert retrieve_obs.source == "section"
        assert "Python" in retrieve_obs.content["text"]

        # 2. Update session to a new position
        session_tool.execute(
            SessionAction(
                command="update",
                session_id="integration-session-001",
                section_id="section-intro",
                page=2,
                progress_percent=25.0,
            )
        )

        # 3. Add a related Q&A to memory
        memory_tool.run(
            {
                "command": "add",
                "session_id": "integration-session-001",
                "lesson_id": "lesson-integration",
                "question": "What did we learn about Python syntax?",
                "answer": retrieve_obs.content["text"],
            }
        )

        # 4. Verify the session was updated and memory was written
        session_state = session_tool.execute(
            SessionAction(
                command="get",
                session_id="integration-session-001",
            )
        )
        assert session_state.session.current_page == 2
        assert session_state.session.progress_percent == 25.0

        history = memory_tool.run(
            {
                "command": "get_history",
                "session_id": "integration-session-001",
            }
        )
        assert history["total"] == 1
        assert "Python syntax" in history["records"][0]["question"]
