"""
SearchTool for semantic retrieval of lesson content.

Exposes agent-callable search capabilities without embedding implementation details.
Consumes HybridRetriever for the underlying retrieval logic.
"""

from typing import Optional

from src.schemas import RetrievedContextItem
from src.schemas.base import SchemaModel
from src.utils.student import HybridRetriever


class SearchAction(SchemaModel):
    """Input schema for SearchTool."""

    query: str = (...,)  # type: ignore
    top_k: int = 5
    section_filter: Optional[str] = None
    page_filter: Optional[int] = None
    prefer_section_id: Optional[str] = None
    prefer_page: Optional[int] = None
    prefer_script_block_id: Optional[str] = None
    include_script: bool = True


class SearchObservation(SchemaModel):
    """Output schema for SearchTool."""

    results: list[RetrievedContextItem] = (...,)  # type: ignore
    total: int = (...,)  # type: ignore


class SearchTool:
    """
    Search tool for semantic retrieval.

    Wraps HybridRetriever to provide a stable, agent-callable interface.
    Does not承载底层实现细节.
    """

    def __init__(self, retriever: HybridRetriever):
        """
        Initialize SearchTool.

        Args:
            retriever: HybridRetriever instance for underlying retrieval.
        """
        self._retriever = retriever

    def search(self, action: SearchAction) -> SearchObservation:
        """
        Execute semantic search.

        Args:
            action: SearchAction containing query, top_k, and optional filters.

        Returns:
            SearchObservation with results list and total count.

        Filtering semantics:
            - section_filter: only results with matching section_id
            - page_filter: only results with matching page
            - include_script: whether script_block source type is included
        """
        # Build source filter for include_script control
        source_filter = self._build_source_filter(action)

        # Execute retrieval with generous top_k to account for post-filtering
        results = self._retriever.retrieve(
            query=action.query,
            top_k=action.top_k * 3 if action.section_filter or action.page_filter else action.top_k,
            source_filter=source_filter,
            prefer_section_id=action.prefer_section_id,
            prefer_page=action.prefer_page,
            prefer_script_block_id=action.prefer_script_block_id,
        )

        # Apply result-level filtering
        filtered = self._apply_result_filters(results, action)

        # Respect top_k after filtering
        filtered = filtered[: action.top_k]

        return SearchObservation(
            results=filtered,
            total=len(filtered),
        )

    def _build_source_filter(self, action: SearchAction) -> Optional[list[str]]:
        """
        Build source filter list based on include_script flag.

        include_script controls whether script_block source type is allowed.
        section_filter and page_filter are handled at result level, not source type level.

        Args:
            action: SearchAction with include_script flag.

        Returns:
            Optional list of allowed source types.
        """
        if action.include_script:
            return None  # No source filtering when script is included
        else:
            return ["page", "section"]  # Exclude script_block

    def _apply_result_filters(
        self,
        results: list[RetrievedContextItem],
        action: SearchAction,
    ) -> list[RetrievedContextItem]:
        """
        Apply section_id and page filters at result level.

        Args:
            results: Raw results from retriever.
            action: SearchAction with section_filter, page_filter.

        Returns:
            Filtered list of results.
        """
        filtered = results

        # Apply section_filter: match by section_id
        if action.section_filter is not None:
            filtered = [item for item in filtered if item.section_id == action.section_filter]

        # Apply page_filter: match by page number
        if action.page_filter is not None:
            filtered = [item for item in filtered if item.page == action.page_filter]

        return filtered

    def retrieve_by_section(
        self,
        section_id: str,
        top_k: Optional[int] = None,
    ) -> SearchObservation:
        """
        Retrieve all content within a specific section.

        Args:
            section_id: Section identifier to retrieve from.
            top_k: Maximum number of results.

        Returns:
            SearchObservation with results list and total count.
        """
        results = self._retriever.retrieve_by_section(
            section_id=section_id,
            top_k=top_k,
        )

        return SearchObservation(
            results=results,
            total=len(results),
        )
