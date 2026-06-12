import os
import tempfile
from contextlib import suppress

from src.memory import QAHistoryStore, SessionStore, StudentCondenser
from src.schemas.common import (
    LearningSession,
    QAHistoryItem,
    QARecord,
)


class TestSessionStore:
    def setup_method(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.store = SessionStore(db_path=self.db_path)

    def teardown_method(self):
        self.store = None
        with suppress(FileNotFoundError, PermissionError):
            os.unlink(self.db_path)

    def test_save_and_get(self):
        session = LearningSession(
            session_id="s1",
            course_id="c1",
            lesson_id="l1",
            user_id="u1",
            status="active",
            current_section_id="sec1",
            current_page=1,
            progress_percent=10.0,
        )
        saved = self.store.save(session)
        assert saved.session_id == "s1"

        retrieved = self.store.get("s1")
        assert retrieved is not None
        assert retrieved.session_id == "s1"
        assert retrieved.lesson_id == "l1"
        assert retrieved.progress_percent == 10.0

    def test_get_not_found(self):
        assert self.store.get("nonexistent") is None

    def test_update_position(self):
        session = LearningSession(session_id="s2", lesson_id="l1")
        self.store.save(session)

        updated = self.store.update_position("s2", current_section_id="sec2", current_page=5)
        assert updated is not None
        assert updated.current_section_id == "sec2"
        assert updated.current_page == 5

    def test_update_progress(self):
        session = LearningSession(session_id="s3", lesson_id="l1", progress_percent=0.0)
        self.store.save(session)

        updated = self.store.update_progress("s3", progress_percent=50.0)
        assert updated is not None
        assert updated.progress_percent == 50.0

    def test_delete(self):
        session = LearningSession(session_id="s4", lesson_id="l1")
        self.store.save(session)

        assert self.store.delete("s4") is True
        assert self.store.get("s4") is None
        assert self.store.delete("s4") is False


class TestQAHistoryStore:
    def setup_method(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.store = QAHistoryStore(db_path=self.db_path)

    def teardown_method(self):
        self.store = None
        with suppress(FileNotFoundError, PermissionError):
            os.unlink(self.db_path)

    def test_add_and_get_by_session(self):
        record = QARecord(
            qa_record_id="q1",
            lesson_id="l1",
            session_id="s1",
            question="What is Python?",
            answer="A programming language.",
        )
        self.store.add(record)

        items = self.store.get_by_session("s1")
        assert len(items) == 1
        assert items[0].question == "What is Python?"
        assert items[0].answer == "A programming language."

    def test_get_recent(self):
        for i in range(5):
            record = QARecord(
                qa_record_id=f"q{i}",
                lesson_id="l1",
                session_id=f"s{i}",
                question=f"Q{i}",
                answer=f"A{i}",
            )
            self.store.add(record)

        recent = self.store.get_recent(limit=3)
        assert len(recent) == 3

    def test_search(self):
        record = QARecord(
            qa_record_id="q_search",
            lesson_id="l1",
            session_id="s1",
            question="What is recursion?",
            answer="A function calling itself.",
        )
        self.store.add(record)

        results = self.store.search("recursion")
        assert len(results) == 1
        assert "recursion" in results[0].question.lower()

    def test_count(self):
        record = QARecord(
            qa_record_id="q_count",
            lesson_id="l1",
            session_id="s1",
            question="Q",
            answer="A",
        )
        self.store.add(record)

        assert self.store.count() == 1
        assert self.store.count(lesson_id="l1") == 1
        assert self.store.count(lesson_id="l999") == 0


class TestStudentCondenser:
    def test_condense_retains_recent(self):
        condenser = StudentCondenser(max_items=3)
        qa_history = [QAHistoryItem(qa_record_id=f"q{i}", question=f"Q{i}", answer=f"A{i}") for i in range(5)]
        condensed = condenser.condense(qa_history)
        assert len(condensed) == 3
        assert condensed[0].qa_record_id == "q2"
        assert condensed[2].qa_record_id == "q4"

    def test_condense_no_op_when_small(self):
        condenser = StudentCondenser(max_items=5)
        qa_history = [QAHistoryItem(qa_record_id=f"q{i}", question=f"Q{i}", answer=f"A{i}") for i in range(3)]
        condensed = condenser.condense(qa_history)
        assert len(condensed) == 3
