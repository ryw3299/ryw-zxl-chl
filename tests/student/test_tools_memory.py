"""Tests for MemoryTool."""

import os
import tempfile
from contextlib import suppress

import pytest

from src.memory.history import QAHistoryStore
from src.tools.memory import MemoryTool


class TestMemoryTool:
    def setup_method(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        self.store = QAHistoryStore(db_path=self.db_path)
        self.tool = MemoryTool(store=self.store)

    def teardown_method(self):
        self.tool = None
        self.store = None
        with suppress(FileNotFoundError, PermissionError):
            os.unlink(self.db_path)

    def test_get_history_empty(self):
        result = self.tool.run({"command": "get_history", "session_id": "s1"})
        assert result["records"] == []
        assert result["total"] == 0

    def test_get_history_with_records(self):
        self.tool.run(
            {
                "command": "add",
                "session_id": "s1",
                "lesson_id": "l1",
                "question": "What is Python?",
                "answer": "A language.",
            }
        )
        result = self.tool.run({"command": "get_history", "session_id": "s1"})
        assert result["total"] == 1
        assert len(result["records"]) == 1
        assert result["records"][0]["question"] == "What is Python?"

    def test_add_requires_question_and_answer(self):
        with pytest.raises(ValueError, match="question and answer"):
            self.tool.run(
                {"command": "add", "session_id": "s1", "lesson_id": "l1", "question": "", "answer": ""}
            )

    def test_add_requires_session_and_lesson(self):
        with pytest.raises(ValueError, match="session_id and lesson_id"):
            self.tool.run(
                {"command": "add", "session_id": "", "lesson_id": "", "question": "Q", "answer": "A"}
            )

    def test_add_success(self):
        result = self.tool.run(
            {
                "command": "add",
                "session_id": "s1",
                "lesson_id": "l1",
                "question": "What is recursion?",
                "answer": "A function calling itself.",
            }
        )
        assert result["total"] == 1
        assert len(result["records"]) == 1
        assert result["records"][0]["question"] == "What is recursion?"

    def test_search_requires_keyword(self):
        with pytest.raises(ValueError, match="keyword"):
            self.tool.run({"command": "search", "keyword": ""})

    def test_search_found(self):
        self.tool.run(
            {
                "command": "add",
                "session_id": "s1",
                "lesson_id": "l1",
                "question": "What is recursion?",
                "answer": "A function calling itself.",
            }
        )
        result = self.tool.run({"command": "search", "keyword": "recursion"})
        assert result["total"] == 1
        assert "recursion" in result["records"][0]["question"].lower()

    def test_search_limit(self):
        for i in range(5):
            self.tool.run(
                {
                    "command": "add",
                    "session_id": f"s{i}",
                    "lesson_id": "l1",
                    "question": f"Q{i}",
                    "answer": f"A{i}",
                }
            )
        result = self.tool.run({"command": "search", "keyword": "Q", "limit": 3})
        assert result["total"] == 3

    def test_unknown_command_raises(self):
        with pytest.raises(ValueError, match="unknown memory command"):
            self.tool.run({"command": "unknown"})

    def test_add_with_references(self):
        result = self.tool.run(
            {
                "command": "add",
                "session_id": "s1",
                "lesson_id": "l1",
                "question": "What is a closure?",
                "answer": "A function with captured state.",
                "references": [
                    {"source_type": "lesson", "snippet": "A closure is..."},
                    {"source_type": "script", "snippet": "Closures are defined as..."},
                ],
            }
        )
        assert result["total"] == 1
        assert result["records"][0]["question"] == "What is a closure?"
        assert len(result["records"][0]["references"]) == 2
        assert result["records"][0]["references"][0]["source_type"] == "lesson"
        assert result["records"][0]["references"][1]["source_type"] == "script"
