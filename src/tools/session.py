from typing import Optional

from pydantic import Field

from src.memory.session_store import SessionStore
from src.schemas.base import SchemaModel
from src.schemas.common import LearningSession


class SessionAction(SchemaModel):
    """Input schema for SessionTool."""

    command: str = Field(..., description="Command: 'get' or 'update'")
    session_id: str = Field(..., description="Learning session identifier")
    lesson_id: Optional[str] = Field(default=None, description="Update: set lesson_id")
    section_id: Optional[str] = Field(default=None, description="Update: set current_section_id")
    page: Optional[int] = Field(default=None, description="Update: set current_page")
    script_block_id: Optional[str] = Field(default=None, description="Update: set current_script_block_id")
    progress_percent: Optional[float] = Field(default=None, description="Update: set progress_percent")
    last_action: Optional[str] = Field(default=None, description="Update: set last_action")


class SessionObservation(SchemaModel):
    """Output schema for SessionTool."""

    session: Optional[LearningSession] = Field(default=None, description="Current session snapshot")


class SessionTool:
    """Tool for reading and updating learning session snapshots.

    Depends on: SessionStore (src.memory.session_store)
    """

    def __init__(self, session_store: Optional[SessionStore] = None):
        self._store = session_store or SessionStore()

    def execute(self, action: SessionAction) -> SessionObservation:
        """Execute a session command (get or update).

        Args:
            action: SessionAction with command and parameters.

        Returns:
            SessionObservation with session snapshot or None.

        Raises:
            ValueError: If command is invalid or update lacks required fields.
        """
        if action.command == "get":
            return self._get(action.session_id)
        elif action.command == "update":
            return self._update(action)
        else:
            raise ValueError(f"Unknown command: {action.command}. Expected 'get' or 'update'.")

    def _get(self, session_id: str) -> SessionObservation:
        """Retrieve a session by session_id."""
        session = self._store.get(session_id)
        return SessionObservation(session=session)

    def _update(self, action: SessionAction) -> SessionObservation:
        """Update session fields.

        At least one update field must be provided.
        """
        update_fields = {
            action.section_id,
            action.page,
            action.script_block_id,
            action.progress_percent,
            action.last_action,
        }
        update_fields.discard(None)

        if not update_fields:
            raise ValueError(
                "update command requires at least one update field: "
                "section_id, page, script_block_id, progress_percent, or last_action"
            )

        has_progress = action.progress_percent is not None
        has_position = (
            action.section_id is not None or action.page is not None or action.script_block_id is not None
        )

        if has_progress:
            session = self._store.update_progress(
                session_id=action.session_id,
                progress_percent=action.progress_percent,
                current_section_id=action.section_id,
                current_page=action.page,
                current_script_block_id=action.script_block_id,
                last_action=action.last_action,
            )
        elif has_position:
            session = self._store.update_position(
                session_id=action.session_id,
                current_section_id=action.section_id,
                current_page=action.page,
                current_script_block_id=action.script_block_id,
            )
        else:
            raise ValueError("update command requires at least one update field")

        return SessionObservation(session=session)
