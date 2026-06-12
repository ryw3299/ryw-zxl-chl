"""
.. deprecated::
    ``SessionStore`` is superseded by ``src.services.student.session_service.SessionService``
    which stores session state in MySQL ``qa_sessions`` instead of a per-request temporary
    SQLite file.  This module is kept for backward compatibility with the legacy agent path
    and will be removed in a future version.
"""

import sqlite3
import warnings
from contextlib import closing
from pathlib import Path
from typing import Optional

from src.schemas.common import LearningSession
from src.utils.paths import paths


class SessionStore:
    """SQLite-backed LearningSession storage (DEPRECATED)."""

    def __init__(self, db_path: Optional[str] = None):
        # Default to the centrally-managed runtime location instead of the
        # legacy hard-coded ``data/student_sessions.db``.
        self.db_path = db_path or str(paths.session_db)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        warnings.warn(
            "SessionStore is deprecated; use src.services.student.session_service.SessionService instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._init_db()

    def _init_db(self) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    course_id TEXT,
                    lesson_id TEXT NOT NULL,
                    user_id TEXT,
                    status TEXT DEFAULT 'active',
                    current_section_id TEXT,
                    current_page INTEGER,
                    current_script_block_id TEXT,
                    progress_percent REAL DEFAULT 0.0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_lesson
                ON sessions(lesson_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user
                ON sessions(user_id)
            """)
            conn.commit()

    def get(self, session_id: str) -> Optional[LearningSession]:
        """Retrieve a session by session_id. Returns None if not found."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            if row is None:
                return None
            return LearningSession(
                session_id=row["session_id"],
                course_id=row["course_id"],
                lesson_id=row["lesson_id"],
                user_id=row["user_id"],
                status=row["status"],
                current_section_id=row["current_section_id"],
                current_page=row["current_page"],
                current_script_block_id=row["current_script_block_id"],
                progress_percent=row["progress_percent"],
            )

    def save(self, session: LearningSession) -> LearningSession:
        """Insert or replace a session."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO sessions (
                    session_id, course_id, lesson_id, user_id, status,
                    current_section_id, current_page, current_script_block_id,
                    progress_percent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session.session_id,
                    session.course_id,
                    session.lesson_id,
                    session.user_id,
                    session.status if session.status else "active",
                    session.current_section_id,
                    session.current_page,
                    session.current_script_block_id,
                    session.progress_percent,
                ),
            )
            conn.commit()
        return session

    def update_position(
        self,
        session_id: str,
        *,
        current_section_id: Optional[str] = None,
        current_page: Optional[int] = None,
        current_script_block_id: Optional[str] = None,
    ) -> Optional[LearningSession]:
        """Update position fields of a session. Returns updated session or None if not found."""
        session = self.get(session_id)
        if session is None:
            return None

        if current_section_id is not None:
            session.current_section_id = current_section_id
        if current_page is not None:
            session.current_page = current_page
        if current_script_block_id is not None:
            session.current_script_block_id = current_script_block_id

        return self.save(session)

    def update_progress(
        self,
        session_id: str,
        *,
        progress_percent: float,
        current_section_id: Optional[str] = None,
        current_page: Optional[int] = None,
        current_script_block_id: Optional[str] = None,
        last_action: Optional[str] = None,
    ) -> Optional[LearningSession]:
        """Update progress fields of a session. Returns updated session or None if not found."""
        session = self.get(session_id)
        if session is None:
            return None

        session.progress_percent = max(0.0, min(100.0, progress_percent))
        if current_section_id is not None:
            session.current_section_id = current_section_id
        if current_page is not None:
            session.current_page = current_page
        if current_script_block_id is not None:
            session.current_script_block_id = current_script_block_id

        return self.save(session)

    def delete(self, session_id: str) -> bool:
        """Delete a session. Returns True if deleted, False if not found."""
        with closing(sqlite3.connect(self.db_path)) as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return cursor.rowcount > 0
