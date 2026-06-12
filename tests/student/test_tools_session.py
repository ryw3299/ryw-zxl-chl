"""Minimal tests for SessionTool."""

import os
import tempfile

import pytest

from src.memory.session_store import SessionStore
from src.schemas.common import LearningSession
from src.tools.session import SessionAction, SessionTool


@pytest.fixture
def session_store():
    """Create a temporary session store for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_sessions.db")
        store = SessionStore(db_path=db_path)
        yield store


@pytest.fixture
def session_tool(session_store):
    """Create a SessionTool with test store."""
    return SessionTool(session_store=session_store)


@pytest.fixture
def sample_session(session_store):
    """Create and save a sample session."""
    session = LearningSession(
        session_id="test-session-001",
        course_id="course-001",
        lesson_id="lesson-001",
        user_id="user-001",
        status="active",
        current_section_id="section-1",
        current_page=1,
        current_script_block_id="block-1",
        progress_percent=10.0,
    )
    return session_store.save(session)


class TestSessionToolGet:
    """Tests for SessionTool get command."""

    def test_get_existing_session(self, session_tool, sample_session):
        """get command returns session when it exists."""
        result = session_tool.execute(SessionAction(command="get", session_id="test-session-001"))

        assert result.session is not None
        assert result.session.session_id == "test-session-001"
        assert result.session.lesson_id == "lesson-001"
        assert result.session.progress_percent == 10.0

    def test_get_nonexistent_session(self, session_tool):
        """get command returns None for missing session."""
        result = session_tool.execute(SessionAction(command="get", session_id="nonexistent"))

        assert result.session is None


class TestSessionToolUpdate:
    """Tests for SessionTool update command."""

    def test_update_progress(self, session_tool, sample_session):
        """update command can update progress_percent."""
        result = session_tool.execute(
            SessionAction(
                command="update",
                session_id="test-session-001",
                progress_percent=50.0,
            )
        )

        assert result.session is not None
        assert result.session.progress_percent == 50.0

    def test_update_position(self, session_tool, sample_session):
        """update command can update position fields."""
        result = session_tool.execute(
            SessionAction(
                command="update",
                session_id="test-session-001",
                section_id="section-5",
                page=10,
            )
        )

        assert result.session is not None
        assert result.session.current_section_id == "section-5"
        assert result.session.current_page == 10

    def test_update_requires_at_least_one_field(self, session_tool, sample_session):
        """update command raises error when no fields provided."""
        with pytest.raises(ValueError, match="at least one update field"):
            session_tool.execute(SessionAction(command="update", session_id="test-session-001"))

    def test_update_nonexistent_session_returns_none(self, session_tool):
        """update command returns None session when session not found."""
        result = session_tool.execute(
            SessionAction(
                command="update",
                session_id="nonexistent",
                progress_percent=50.0,
            )
        )

        assert result.session is None


class TestSessionToolValidation:
    """Tests for SessionTool command validation."""

    def test_invalid_command_raises_error(self, session_tool):
        """Unknown command raises ValueError."""
        with pytest.raises(ValueError, match="Unknown command"):
            session_tool.execute(SessionAction(command="invalid", session_id="test"))
