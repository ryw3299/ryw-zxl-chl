"""SearchOpenHandsTool - OpenHands adapter for semantic search tool."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ClassVar, Optional

from openhands.sdk.llm import TextContent
from openhands.sdk.tool import Action, Observation, ToolAnnotations, ToolDefinition, ToolExecutor
from openhands.sdk.tool.registry import register_tool
from pydantic import Field

from src.schemas import RetrievedContextItem, StructuredLessonContent
from src.schemas.generate_schemas import LessonScript
from src.tools.search import SearchAction as BusinessSearchAction
from src.tools.search import SearchObservation as BusinessSearchObservation
from src.tools.search import SearchTool as BusinessSearchTool


class SearchAction(Action):
    """Input schema for SearchOpenHandsTool.

    Attributes:
        query: Student question or search keyword.
        top_k: Number of results to return (default 5).
        section_filter: Optional section ID to limit results.
        page_filter: Optional page number to limit results.
        prefer_section_id: Optional preferred section ID for soft ranking.
        prefer_page: Optional preferred page number for soft ranking.
        prefer_script_block_id: Optional preferred script block ID for soft ranking.
        include_script: Whether to include script_block source type (default True).
    """

    query: str = Field(description="Student question or search keyword")
    top_k: int = Field(default=5, description="Number of results to return")
    section_filter: Optional[str] = Field(default=None, description="Optional section ID to limit results")
    page_filter: Optional[int] = Field(default=None, description="Optional page number to limit results")
    prefer_section_id: Optional[str] = Field(
        default=None, description="Preferred section ID for soft ranking boost"
    )
    prefer_page: Optional[int] = Field(
        default=None, description="Preferred page number for soft ranking boost"
    )
    prefer_script_block_id: Optional[str] = Field(
        default=None, description="Preferred script block ID for soft ranking boost"
    )
    include_script: bool = Field(default=True, description="Whether to include script_block source type")


class SearchObservation(Observation):
    """Output schema for SearchOpenHandsTool.

    Attributes:
        results: List of retrieved context items.
        total: Total number of results returned.
    """

    results: list[RetrievedContextItem] = Field(
        default_factory=list,
        description="List of retrieved context items",
    )
    total: int = Field(default=0, description="Total number of results returned")


class SearchExecutor(ToolExecutor[SearchAction, SearchObservation]):
    """Executor that delegates to the business SearchTool."""

    def __init__(self, business_tool: BusinessSearchTool):
        self._business_tool = business_tool

    def __call__(self, action: SearchAction, conversation: Any | None = None) -> SearchObservation:
        """Execute search by delegating to the business tool.

        Args:
            action: SearchAction with query and filters.
            conversation: Optional conversation context (unused).

        Returns:
            SearchObservation with results and total.
        """
        # Convert OpenHands Action to business Action
        business_action = BusinessSearchAction(
            query=action.query,
            top_k=action.top_k,
            section_filter=action.section_filter,
            page_filter=action.page_filter,
            prefer_section_id=action.prefer_section_id,
            prefer_page=action.prefer_page,
            prefer_script_block_id=action.prefer_script_block_id,
            include_script=action.include_script,
        )

        # Delegate to business tool
        business_obs: BusinessSearchObservation = self._business_tool.search(business_action)

        # Build LLM-readable content summary
        content = self._build_content(business_obs)

        # Convert business Observation to OpenHands Observation
        return SearchObservation(
            results=business_obs.results,
            total=business_obs.total,
            content=content,
        )

    def _build_content(self, business_obs: BusinessSearchObservation) -> list[TextContent]:
        """Build LLM-readable content from business observation."""
        if business_obs.total == 0:
            return [TextContent(text="No results found for the query.")]

        lines = [f"Found {business_obs.total} result(s):"]
        for i, item in enumerate(business_obs.results, 1):
            lines.append(f"{i}. [{item.source}] {item.title}")
            if item.text:
                # Truncate long text
                text_preview = item.text[:100] + "..." if len(item.text) > 100 else item.text
                lines.append(f"   {text_preview}")

        return [TextContent(text="\n".join(lines))]


SEARCH_TOOL_DESCRIPTION = """Search for relevant lesson content based on student question.

This tool performs semantic search across lesson content (pages, sections, and scripts).
Use this when a student asks a question that requires retrieving relevant background content.

### Search Parameters
- query: The student question or search keyword (required)
- top_k: Number of results to return (default 5)
- section_filter: Optional - limit results to a specific section
- page_filter: Optional - limit results to a specific page number
- prefer_section_id: Optional - softly boost results from the current section
- prefer_page: Optional - softly boost results from the current page
- prefer_script_block_id: Optional - softly boost results from the current script block
- include_script: Whether to include script_block results (default True)

### Returns
- results: List of retrieved context items with source, title, text, and scores
- total: Total number of results returned
"""


class SearchOpenHandsTool(ToolDefinition[SearchAction, SearchObservation]):
    """OpenHands ToolDefinition adapter for SearchTool.

    Wraps the business SearchTool to conform to OpenHands SDK patterns.
    """

    name: ClassVar[str] = "search"

    @classmethod
    def create(
        cls,
        conv_state: Any = None,
        **params: Any,
    ) -> Sequence[SearchOpenHandsTool]:
        """Create a SearchOpenHandsTool instance.

        Args:
            conv_state: Optional conversation state (passed by OpenHands SDK).
            **params: Injected dependencies:
                - structured_content: StructuredLessonContent (REQUIRED)
                - lesson_script: LessonScript (optional)

        Returns:
            Sequence containing a single SearchOpenHandsTool instance.

        Raises:
            ValueError: If structured_content is not provided.
        """
        from src.utils.student import RetrieverFactory

        # Accept injected dependencies from params
        structured_content: Optional[StructuredLessonContent] = params.get("structured_content")
        lesson_script: Optional[LessonScript] = params.get("lesson_script")

        # Fail explicitly if required dependency is missing
        if structured_content is None:
            raise ValueError(
                "SearchOpenHandsTool.create() requires 'structured_content' to be injected. "
                "This tool cannot function without structured lesson content."
            )

        # Initialize business tool with injected dependencies
        retriever = RetrieverFactory.get_or_create(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )
        business_tool = BusinessSearchTool(retriever=retriever)

        # Create executor
        executor = SearchExecutor(business_tool=business_tool)

        return [
            cls(
                action_type=SearchAction,
                observation_type=SearchObservation,
                description=SEARCH_TOOL_DESCRIPTION,
                annotations=ToolAnnotations(
                    title="search",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
                executor=executor,
            )
        ]


# Register the tool
register_tool("search", SearchOpenHandsTool)
