"""RetrieveOpenHandsTool - OpenHands adapter for precise content retrieval."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ClassVar, Literal, Optional

from openhands.sdk.llm import TextContent
from openhands.sdk.tool import Action, Observation, ToolAnnotations, ToolDefinition, ToolExecutor
from openhands.sdk.tool.registry import register_tool
from pydantic import Field

from src.schemas import StructuredLessonContent
from src.schemas.generate_schemas import LessonScript
from src.tools.retrieve import RetrieveAction as BusinessRetrieveAction
from src.tools.retrieve import RetrieveObservation as BusinessRetrieveObservation
from src.tools.retrieve import RetrieveTool as BusinessRetrieveTool


class RetrieveAction(Action):
    """Input schema for RetrieveOpenHandsTool.

    Exactly one of page_id, section_id, script_block_id, or page must be provided.

    Attributes:
        page_id: Exact page identifier.
        section_id: Exact section identifier.
        script_block_id: Exact script block identifier.
        page: 1-based page number.
    """

    page_id: Optional[str] = Field(default=None, description="Exact page identifier")
    section_id: Optional[str] = Field(default=None, description="Exact section identifier")
    script_block_id: Optional[str] = Field(default=None, description="Exact script block identifier")
    page: Optional[int] = Field(default=None, description="1-based page number")


class RetrieveObservation(Observation):
    """Output schema for RetrieveOpenHandsTool.

    Attributes:
        content: List of TextContent/ImageContent for LLM consumption.
        retrieved_content: Retrieved content as a dictionary.
        source: Content source type (page, section, or script_block).
    """

    # Note: 'content' is inherited from Observation base class
    retrieved_content: dict[str, Any] = Field(
        default_factory=dict,
        description="Retrieved content as a dictionary",
    )
    source: Literal["page", "section", "script_block"] = Field(
        description="Content source type",
    )


class RetrieveExecutor(ToolExecutor[RetrieveAction, RetrieveObservation]):
    """Executor that delegates to the business RetrieveTool."""

    def __init__(self, business_tool: BusinessRetrieveTool):
        self._business_tool = business_tool

    def __call__(self, action: RetrieveAction, conversation: Any | None = None) -> RetrieveObservation:
        """Execute precise retrieval by delegating to the business tool.

        Args:
            action: RetrieveAction specifying what to retrieve.
            conversation: Optional conversation context (unused).

        Returns:
            RetrieveObservation with content and source.

        Raises:
            ValueError: If validation fails or content not found.
        """
        # Check that exactly one field is provided
        provided = [
            action.page_id is not None,
            action.section_id is not None,
            action.script_block_id is not None,
            action.page is not None,
        ]
        if not any(provided):
            return self._error_obs(
                "Exactly one of page_id, section_id, script_block_id, or page must be provided"
            )
        if sum(provided) > 1:
            return self._error_obs(
                "Only one of page_id, section_id, script_block_id, or page can be provided at a time"
            )

        # Convert OpenHands Action to business Action
        business_action = BusinessRetrieveAction(
            page_id=action.page_id,
            section_id=action.section_id,
            script_block_id=action.script_block_id,
            page=action.page,
        )

        try:
            # Delegate to business tool
            business_obs: BusinessRetrieveObservation = self._business_tool.retrieve(business_action)

            # Build LLM-readable content summary
            content = self._build_content(business_obs)

            # Convert business Observation to OpenHands Observation
            return RetrieveObservation(
                retrieved_content=business_obs.content,
                source=business_obs.source,
                content=content,
            )
        except ValueError as e:
            # Content not found or validation error
            return self._error_obs(str(e))

    def _error_obs(self, message: str) -> RetrieveObservation:
        """Create an error observation with proper TextContent."""
        return RetrieveObservation(
            retrieved_content={},
            source="page",
            is_error=True,
            content=[TextContent(text=f"Error: {message}")],
        )

    def _build_content(self, business_obs: BusinessRetrieveObservation) -> list[TextContent]:
        """Build LLM-readable content from business observation."""
        content_dict = business_obs.content
        title = content_dict.get("title", "Untitled")
        text = content_dict.get("text", "")
        source = business_obs.source

        lines = [
            f"[{source.upper()}] {title}",
            "",
            text if text else "(No content)",
        ]
        return [TextContent(text="\n".join(lines))]


RETRIEVE_TOOL_DESCRIPTION = """Precisely retrieve lesson content by exact identifier.

This tool performs exact lookups of lesson content without semantic search.
Use this when you have a specific page_id, section_id, script_block_id, or page number.

### Parameters (exactly one required)
- page_id: Exact page identifier
- section_id: Exact section identifier
- script_block_id: Exact script block identifier
- page: 1-based page number

### Returns
- retrieved_content: Retrieved content dictionary with title, text, and metadata
- source: Type of content source (page, section, or script_block)
"""


class RetrieveOpenHandsTool(ToolDefinition[RetrieveAction, RetrieveObservation]):
    """OpenHands ToolDefinition adapter for RetrieveTool.

    Wraps the business RetrieveTool to conform to OpenHands SDK patterns.
    """

    name: ClassVar[str] = "retrieve"

    @classmethod
    def create(
        cls,
        conv_state: Any = None,
        **params: Any,
    ) -> Sequence[RetrieveOpenHandsTool]:
        """Create a RetrieveOpenHandsTool instance.

        Args:
            conv_state: Optional conversation state (passed by OpenHands SDK).
            **params: Injected dependencies:
                - structured_content: StructuredLessonContent (REQUIRED)
                - lesson_script: LessonScript (optional)

        Returns:
            Sequence containing a single RetrieveOpenHandsTool instance.

        Raises:
            ValueError: If structured_content is not provided.
        """
        from src.utils.student import ContentGetter

        # Accept injected dependencies from params
        structured_content: Optional[StructuredLessonContent] = params.get("structured_content")
        lesson_script: Optional[LessonScript] = params.get("lesson_script")

        # Fail explicitly if required dependency is missing
        if structured_content is None:
            raise ValueError(
                "RetrieveOpenHandsTool.create() requires 'structured_content' to be injected. "
                "This tool cannot function without structured lesson content."
            )

        # Initialize business tool with injected dependencies
        content_getter = ContentGetter(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        business_tool = BusinessRetrieveTool(content_getter=content_getter)

        # Create executor
        executor = RetrieveExecutor(business_tool=business_tool)

        return [
            cls(
                action_type=RetrieveAction,
                observation_type=RetrieveObservation,
                description=RETRIEVE_TOOL_DESCRIPTION,
                annotations=ToolAnnotations(
                    title="retrieve",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
                executor=executor,
            )
        ]


# Register the tool
register_tool("retrieve", RetrieveOpenHandsTool)
