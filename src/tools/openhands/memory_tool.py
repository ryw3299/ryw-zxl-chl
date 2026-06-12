"""MemoryOpenHandsTool - OpenHands adapter for QA history operations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ClassVar, Optional

from openhands.sdk.llm import TextContent
from openhands.sdk.tool import Action, Observation, ToolAnnotations, ToolDefinition, ToolExecutor
from openhands.sdk.tool.registry import register_tool
from pydantic import Field

from src.tools.memory import MemoryTool as BusinessMemoryTool


class MemoryAction(Action):
    """Input schema for MemoryOpenHandsTool.

    Attributes:
        command: Command to execute ('get_history', 'add', 'search').
        session_id: Learning session identifier.
        lesson_id: Optional - used when adding a new record.
        question: Optional - question text for 'add' command.
        answer: Optional - answer text for 'add' command.
        references: Optional - list of reference dicts for 'add' command.
        keyword: Optional - search keyword for 'search' command.
        limit: Maximum number of records to return (default 5).
    """

    command: str = Field(description="Command: 'get_history', 'add', or 'search'")
    session_id: str = Field(description="Learning session identifier")
    lesson_id: Optional[str] = Field(default=None, description="Add: set lesson_id")
    question: Optional[str] = Field(default=None, description="Add: set question text")
    answer: Optional[str] = Field(default=None, description="Add: set answer text")
    references: Optional[list[dict[str, Any]]] = Field(
        default=None,
        description="Add: list of reference dicts",
    )
    keyword: Optional[str] = Field(default=None, description="Search: keyword to search")
    limit: int = Field(default=5, description="Maximum number of records to return")


class MemoryObservation(Observation):
    """Output schema for MemoryOpenHandsTool.

    Attributes:
        records: List of QA history records.
        total: Total number of records returned.
    """

    records: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of QA history records",
    )
    total: int = Field(default=0, description="Total number of records returned")


class MemoryExecutor(ToolExecutor[MemoryAction, MemoryObservation]):
    """Executor that delegates to the business MemoryTool."""

    def __init__(self, business_tool: BusinessMemoryTool):
        self._business_tool = business_tool

    def __call__(self, action: MemoryAction, conversation: Any | None = None) -> MemoryObservation:
        """Execute memory command by delegating to the business tool.

        Args:
            action: MemoryAction with command and parameters.
            conversation: Optional conversation context (unused).

        Returns:
            MemoryObservation with records and total.
        """
        # Validate command
        valid_commands = ("get_history", "add", "search")
        if action.command not in valid_commands:
            return self._error_obs(f"Unknown command '{action.command}'. Expected: {valid_commands}")

        # Build action dict for business tool
        business_action: dict[str, Any] = {
            "command": action.command,
            "session_id": action.session_id,
        }

        if action.lesson_id is not None:
            business_action["lesson_id"] = action.lesson_id
        if action.question is not None:
            business_action["question"] = action.question
        if action.answer is not None:
            business_action["answer"] = action.answer
        if action.references is not None:
            business_action["references"] = action.references
        if action.keyword is not None:
            business_action["keyword"] = action.keyword
        if action.limit != 5:  # Only include if non-default
            business_action["limit"] = action.limit

        try:
            # Delegate to business tool
            result: dict[str, Any] = self._business_tool.run(business_action)

            # Build LLM-readable content summary
            content = self._build_content(action.command, result)

            # Convert business result to OpenHands Observation
            return MemoryObservation(
                records=result.get("records", []),
                total=result.get("total", 0),
                content=content,
            )
        except ValueError as e:
            # Validation or execution error
            return self._error_obs(str(e))

    def _error_obs(self, message: str) -> MemoryObservation:
        """Create an error observation with proper TextContent."""
        return MemoryObservation(
            records=[],
            total=0,
            is_error=True,
            content=[TextContent(text=f"Error: {message}")],
        )

    def _build_content(self, command: str, result: dict[str, Any]) -> list[TextContent]:
        """Build LLM-readable content from business result."""
        total = result.get("total", 0)
        records = result.get("records", [])

        if command == "add":
            if total > 0:
                return [TextContent(text=f"QA record added successfully. Total records: {total}")]
            return [TextContent(text="Failed to add QA record.")]

        if command == "get_history":
            if total == 0:
                return [TextContent(text="No QA history found for this session.")]
            lines = [f"QA History ({total} record(s)):"]
            for i, rec in enumerate(records, 1):
                q = rec.get("question", "")[:50]
                a = rec.get("answer", "")[:50]
                lines.append(f"{i}. Q: {q}... A: {a}...")
            return [TextContent(text="\n".join(lines))]

        if command == "search":
            if total == 0:
                return [TextContent(text="No matching records found.")]
            lines = [f"Search results ({total} match(es)):"]
            for i, rec in enumerate(records, 1):
                q = rec.get("question", "")[:50]
                lines.append(f"{i}. {q}...")
            return [TextContent(text="\n".join(lines))]

        return [TextContent(text=f"Processed {command} command.")]


MEMORY_TOOL_DESCRIPTION = """Manage QA history records for student learning sessions.

This tool provides read/write access to question-answer history.
Use this to record new Q&A interactions or search past questions.

### Commands

**get_history**: Retrieve QA history for a session.
- Required: session_id
- Optional: limit (default 5)
- Returns: List of historical Q&A records

**add**: Add a new Q&A record.
- Required: session_id, lesson_id, question, answer
- Optional: references list
- Returns: The created record

**search**: Search QA history by keyword.
- Required: session_id, keyword
- Optional: lesson_id, limit (default 5)
- Returns: List of matching Q&A records

### Record Structure
Each record contains:
- qa_record_id: Unique identifier
- question: The student's question
- answer: The system's answer
- understanding_level: Comprehension level (full/partial/none)
- current_section_id: Section at question time
- current_page: Page number at question time
"""


class MemoryOpenHandsTool(ToolDefinition[MemoryAction, MemoryObservation]):
    """OpenHands ToolDefinition adapter for MemoryTool.

    Wraps the business MemoryTool to conform to OpenHands SDK patterns.
    """

    name: ClassVar[str] = "memory"

    @classmethod
    def create(
        cls,
        conv_state: Any = None,
        **params: Any,
    ) -> Sequence[MemoryOpenHandsTool]:
        """Create a MemoryOpenHandsTool instance.

        Args:
            conv_state: Optional conversation state (passed by OpenHands SDK).
            **params: Injected dependencies:
                - history_store: QAHistoryStore instance (preferred)
                - history_db_path: SQLite path used to build QAHistoryStore

        Returns:
            Sequence containing a single MemoryOpenHandsTool instance.

        Raises:
            ValueError: If neither history_store nor history_db_path is provided.
        """
        from src.memory.history import QAHistoryStore

        # Accept injected history_store or a serialized db path.
        history_store: QAHistoryStore = params.get("history_store")
        history_db_path: str | None = params.get("history_db_path")
        if history_store is None and history_db_path:
            history_store = QAHistoryStore(history_db_path)
        if history_store is None:
            raise ValueError(
                "MemoryOpenHandsTool.create() requires 'history_store' or "
                "'history_db_path' to be injected. This tool cannot function "
                "without a QA history store."
            )

        # Initialize business tool
        business_tool = BusinessMemoryTool(store=history_store)

        # Create executor
        executor = MemoryExecutor(business_tool=business_tool)

        return [
            cls(
                action_type=MemoryAction,
                observation_type=MemoryObservation,
                description=MEMORY_TOOL_DESCRIPTION,
                annotations=ToolAnnotations(
                    title="memory",
                    readOnlyHint=False,
                    destructiveHint=False,
                    idempotentHint=False,
                    openWorldHint=False,
                ),
                executor=executor,
            )
        ]


# Register the tool
register_tool("memory", MemoryOpenHandsTool)
