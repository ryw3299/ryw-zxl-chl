"""
.. deprecated::
    ``QAHistoryStore`` is superseded by ``src.services.student.conversation_service.ConversationService``
    which uses OpenHands Conversation persistence and MySQL ``qa_records``.
    This module is kept for backward compatibility with the legacy agent path
    and will be removed in a future version.
"""

import json
import sqlite3
import warnings
from contextlib import closing
from pathlib import Path
from typing import Optional

from src.schemas.common import QAHistoryItem, QARecord
from src.utils.paths import paths


class QAHistoryStore:
    """SQLite-backed QA record storage (DEPRECATED)."""

    def __init__(self, db_path: Optional[str] = None):
        # Default to the centrally-managed runtime location instead of the
        # legacy hard-coded ``data/student_qa_history.db``.
        self.db_path = db_path or str(paths.history_db)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        warnings.warn(
            "QAHistoryStore is deprecated; use "
            "src.services.student.conversation_service.ConversationService instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._init_db()

    def _init_db(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS qa_history (
                    qa_record_id TEXT PRIMARY KEY,
                    course_id TEXT,
                    lesson_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    current_section_id TEXT,
                    current_page INTEGER,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    understanding_level TEXT,
                    references_json TEXT DEFAULT '[]',
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_qa_session
                ON qa_history(session_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_qa_lesson
                ON qa_history(lesson_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_qa_created
                ON qa_history(created_at)
            """)
            conn.commit()

    def add(self, record: QARecord) -> QARecord:
        """Insert a new QA record."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            understanding_level = record.understanding_level
            if understanding_level is not None and hasattr(understanding_level, "value"):
                understanding_level = understanding_level.value
            references_json = json.dumps([ref.model_dump() for ref in record.references])
            conn.execute(
                """
                INSERT INTO qa_history (
                    qa_record_id, course_id, lesson_id, session_id,
                    current_section_id, current_page, question, answer,
                    understanding_level, references_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    record.qa_record_id,
                    record.course_id,
                    record.lesson_id,
                    record.session_id,
                    record.current_section_id,
                    record.current_page,
                    record.question,
                    record.answer,
                    understanding_level,
                    references_json,
                ),
            )
            conn.commit()
        return record

    def get_by_session(self, session_id: str) -> list[QAHistoryItem]:
        """Retrieve QA history items for a session, ordered by creation time."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT qa_record_id, question, answer, understanding_level,
                       current_section_id, current_page
                FROM qa_history
                WHERE session_id = ?
                ORDER BY created_at ASC
                """,
                (session_id,),
            ).fetchall()
            return [
                QAHistoryItem(
                    qa_record_id=row["qa_record_id"],
                    question=row["question"],
                    answer=row["answer"],
                    understanding_level=row["understanding_level"] if row["understanding_level"] else None,
                    current_section_id=row["current_section_id"],
                    current_page=row["current_page"],
                )
                for row in rows
            ]

    def get_recent(self, limit: int = 10) -> list[QAHistoryItem]:
        """Retrieve the most recent QA history items across all sessions."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT qa_record_id, question, answer, understanding_level,
                       current_section_id, current_page
                FROM qa_history
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [
                QAHistoryItem(
                    qa_record_id=row["qa_record_id"],
                    question=row["question"],
                    answer=row["answer"],
                    understanding_level=row["understanding_level"] if row["understanding_level"] else None,
                    current_section_id=row["current_section_id"],
                    current_page=row["current_page"],
                )
                for row in rows
            ]

    def search(self, keyword: str, lesson_id: Optional[str] = None, limit: int = 20) -> list[QAHistoryItem]:
        """Search QA records by keyword in question or answer."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            pattern = f"%{keyword}%"
            if lesson_id:
                rows = conn.execute(
                    """
                    SELECT qa_record_id, question, answer, understanding_level,
                           current_section_id, current_page
                    FROM qa_history
                    WHERE (question LIKE ? OR answer LIKE ?) AND lesson_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (pattern, pattern, lesson_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT qa_record_id, question, answer, understanding_level,
                           current_section_id, current_page
                    FROM qa_history
                    WHERE question LIKE ? OR answer LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (pattern, pattern, limit),
                ).fetchall()
            return [
                QAHistoryItem(
                    qa_record_id=row["qa_record_id"],
                    question=row["question"],
                    answer=row["answer"],
                    understanding_level=row["understanding_level"] if row["understanding_level"] else None,
                    current_section_id=row["current_section_id"],
                    current_page=row["current_page"],
                )
                for row in rows
            ]

    def count(self, session_id: Optional[str] = None, lesson_id: Optional[str] = None) -> int:
        """Count QA records, optionally filtered by session_id or lesson_id."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            if session_id:
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM qa_history WHERE session_id = ?", (session_id,)
                ).fetchone()
            elif lesson_id:
                row = conn.execute(
                    "SELECT COUNT(*) as cnt FROM qa_history WHERE lesson_id = ?", (lesson_id,)
                ).fetchone()
            else:
                row = conn.execute("SELECT COUNT(*) as cnt FROM qa_history").fetchone()
            return row[0]
