"""Session management backed by MySQL ``qa_sessions``.

Replaces the per-request temporary SQLite ``SessionStore`` so that session
state survives across requests and works in multi-instance deployments.
"""

from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session as DBSession

from src.api.models.tables import QASession
from src.schemas.common import LearningSession

logger = logging.getLogger(__name__)


class SessionService:
    @staticmethod
    def get_or_init(
        db: DBSession,
        *,
        session_id: str,
        user_id: str,
        school_id: Optional[str] = None,
        course_id: str,
        lesson_id: str,
    ) -> LearningSession:
        """Return the current session state, creating a row if needed."""
        row = db.query(QASession).filter(QASession.session_id == session_id).first()
        if row is None:
            row = QASession(
                session_id=session_id,
                user_id=user_id,
                school_id=school_id,
                course_id=course_id,
                lesson_id=lesson_id,
                status="active",
            )
            db.add(row)
            db.commit()
            db.refresh(row)

        return LearningSession(
            session_id=row.session_id,
            course_id=row.course_id,
            lesson_id=row.lesson_id,
            user_id=row.user_id,
            status=row.status or "active",
            current_section_id=getattr(row, "current_section_id", None),
            current_page=getattr(row, "current_page", None),
            current_script_block_id=getattr(row, "current_script_block_id", None),
            progress_percent=getattr(row, "progress_percent", 0.0) or 0.0,
        )

    @staticmethod
    def update_position(
        db: DBSession,
        session_id: str,
        *,
        current_section_id: Optional[str] = None,
        current_page: Optional[int] = None,
        current_script_block_id: Optional[str] = None,
        progress_percent: Optional[float] = None,
        last_action: Optional[str] = None,
    ) -> None:
        """Persist position / progress updates back to MySQL."""
        row = db.query(QASession).filter(QASession.session_id == session_id).first()
        if row is None:
            logger.warning("update_position: session %s not found", session_id)
            return
        if current_section_id is not None and hasattr(row, "current_section_id"):
            row.current_section_id = current_section_id  # type: ignore[attr-defined]
        if current_page is not None and hasattr(row, "current_page"):
            row.current_page = current_page  # type: ignore[attr-defined]
        if current_script_block_id is not None and hasattr(row, "current_script_block_id"):
            row.current_script_block_id = current_script_block_id  # type: ignore[attr-defined]
        if progress_percent is not None and hasattr(row, "progress_percent"):
            row.progress_percent = max(0.0, min(100.0, progress_percent))  # type: ignore[attr-defined]
        if last_action is not None and hasattr(row, "last_action"):
            row.last_action = last_action  # type: ignore[attr-defined]
        db.commit()
