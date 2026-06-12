"""SessionOpenHandsTool - OpenHands adapter for learning session operations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ClassVar, Optional

from openhands.sdk.llm import TextContent
from openhands.sdk.tool import Action, Observation, ToolAnnotations, ToolDefinition, ToolExecutor
from openhands.sdk.tool.registry import register_tool
from pydantic import Field

from src.schemas.common import LearningSession
from src.tools.session import SessionAction as BusinessSessionAction
from src.tools.session import SessionObservation as BusinessSessionObservation
from src.tools.session import SessionTool as BusinessSessionTool


class SessionAction(Action):
    """Input schema for SessionOpenHandsTool.

    Attributes:
        command: Command to execute ('get' or 'update').
        session_id: Learning session identifier.
        lesson_id: Optional - set when updating with lesson_id.
        section_id: Optional - update current section.
        page: Optional - update current page.
        script_block_id: Optional - update current script block.
        progress_percent: Optional - update progress percentage.
        last_action: Optional - update last action.
    """

    command: str = Field(description="Command: 'get' or 'update'")
    session_id: str = Field(description="Learning session identifier")
    lesson_id: Optional[str] = Field(default=None, description="Update: set lesson_id")
    section_id: Optional[str] = Field(default=None, description="Update: set current section")
    page: Optional[int] = Field(default=None, description="Update: set current page")
    script_block_id: Optional[str] = Field(default=None, description="Update: set current script block")
    progress_percent: Optional[float] = Field(default=None, description="Update: set progress percentage")
    last_action: Optional[str] = Field(default=None, description="Update: set last action")


class SessionObservation(Observation):
    """Output schema for SessionOpenHandsTool.

    Attributes:
        session: Current session snapshot, or None if not found.
    """

    session: Optional[LearningSession] = Field(
        default=None,
        description="Current session snapshot",
    )


class SessionExecutor(ToolExecutor[SessionAction, SessionObservation]):
    """Executor that delegates to the business SessionTool."""

    def __init__(self, business_tool: BusinessSessionTool):
        self._business_tool = business_tool

    def __call__(self, action: SessionAction, conversation: Any | None = None) -> SessionObservation:
        """Execute session command by delegating to the business tool.

        Args:
            action: SessionAction with command and parameters.
            conversation: Optional conversation context (unused).

        Returns:
            SessionObservation with session snapshot or error.
        """
        # Validate command
        if action.command not in ("get", "update"):
            return self._error_obs(f"Unknown command '{action.command}'. Expected 'get' or 'update'.")

        # Convert OpenHands Action to business Action
        business_action = BusinessSessionAction(
            command=action.command,
            session_id=action.session_id,
            lesson_id=action.lesson_id,
            section_id=action.section_id,
            page=action.page,
            script_block_id=action.script_block_id,
            progress_percent=action.progress_percent,
            last_action=action.last_action,
        )

        try:
            # Delegate to business tool
            business_obs: BusinessSessionObservation = self._business_tool.execute(business_action)

            # Build LLM-readable content summary
            content = self._build_content(business_obs)

            # Convert business Observation to OpenHands Observation
            return SessionObservation(
                session=business_obs.session,
                content=content,
            )
        except ValueError as e:
            # Validation or execution error
            return self._error_obs(str(e))

    def _error_obs(self, message: str) -> SessionObservation:
        """Create an error observation with proper TextContent."""
        return SessionObservation(
            session=None,
            is_error=True,
            content=[TextContent(text=f"Error: {message}")],
        )

    def _build_content(self, business_obs: BusinessSessionObservation) -> list[TextContent]:
        """Build LLM-readable content from business observation."""
        session = business_obs.session
        if session is None:
            return [TextContent(text="Session not found.")]

        lines = [
            f"Session: {session.session_id}",
            f"Status: {session.status}",
            f"Progress: {session.progress_percent}%",
        ]
        if session.current_section_id:
            lines.append(f"Section: {session.current_section_id}")
        if session.current_page is not None:
            lines.append(f"Page: {session.current_page}")
        if session.current_script_block_id:
            lines.append(f"Script Block: {session.current_script_block_id}")

        return [TextContent(text="\n".join(lines))]


SESSION_TOOL_DESCRIPTION = """Read and update learning session snapshots.

This tool manages student learning sessions, tracking progress through lessons.
Use 'get' to retrieve a session and 'update' to modify session state.

### Commands

**get**: Retrieve a session by session_id.
- Required: session_id
- Returns: Current session snapshot

**update**: Update session fields.
- Required: session_id, plus at least one update field
- Optional: lesson_id, section_id, page, script_block_id, progress_percent, last_action
- Returns: Updated session snapshot

### Use Cases
- get: Check current learning progress
- update: Record position changes, progress, or actions
"""


class SessionOpenHandsTool(ToolDefinition[SessionAction, SessionObservation]):
    """OpenHands ToolDefinition adapter for SessionTool.

    Wraps the business SessionTool to conform to OpenHands SDK patterns.
    """

    name: ClassVar[str] = "session"

    @classmethod
    def create(
        cls,
        conv_state: Any = None,
        **params: Any,
    ) -> Sequence[SessionOpenHandsTool]:
        """Create a SessionOpenHandsTool instance.

        Args:
            conv_state: Optional conversation state (passed by OpenHands SDK).
            **params: Injected dependencies:
                - session_store: SessionStore instance (preferred)
                - session_db_path: SQLite path used to build SessionStore

        Returns:
            Sequence containing a single SessionOpenHandsTool instance.

        Raises:
            ValueError: If neither session_store nor session_db_path is provided.
        """
        from src.memory.session_store import SessionStore

        # Accept injected session_store or a serialized db path.
        session_store: SessionStore = params.get("session_store")
        session_db_path: str | None = params.get("session_db_path")
        if session_store is None and session_db_path:
            session_store = SessionStore(session_db_path)
        if session_store is None:
            raise ValueError(
                "SessionOpenHandsTool.create() requires 'session_store' or "
                "'session_db_path' to be injected. This tool cannot function "
                "without a session store."
            )

        # Initialize business tool
        business_tool = BusinessSessionTool(session_store=session_store)

        # Create executor
        executor = SessionExecutor(business_tool=business_tool)

        return [
            cls(
                action_type=SessionAction,
                observation_type=SessionObservation,
                description=SESSION_TOOL_DESCRIPTION,
                annotations=ToolAnnotations(
                    title="session",
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=False,
                    openWorldHint=False,
                ),
                executor=executor,
            )
        ]


# Register the tool
register_tool("session", SessionOpenHandsTool)
