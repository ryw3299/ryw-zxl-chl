"""
RetrieveTool - precise content retrieval without semantic search.

This tool provides exact lookup of lesson content by page_id, section_id,
script_block_id, or page number. It delegates to ContentGetter.
"""

from typing import Any, Literal, Optional

from pydantic import Field, model_validator

from src.schemas import RetrievedContextItem
from src.schemas.base import SchemaModel
from src.utils.student import ContentGetter


class RetrieveAction(SchemaModel):
    """Action input for RetrieveTool.

    Exactly one of page_id, section_id, script_block_id, or page must be provided.
    """

    page_id: Optional[str] = Field(default=None, description="Exact page identifier")
    section_id: Optional[str] = Field(default=None, description="Exact section identifier")
    script_block_id: Optional[str] = Field(default=None, description="Exact script block identifier")
    page: Optional[int] = Field(default=None, description="1-based page number")

    @model_validator(mode="after")
    def check_exclusive_fields(self) -> "RetrieveAction":
        """Ensure exactly one field is provided."""
        provided = [
            self.page_id is not None,
            self.section_id is not None,
            self.script_block_id is not None,
            self.page is not None,
        ]
        if not any(provided):
            raise ValueError("Exactly one of page_id, section_id, script_block_id, or page must be provided")
        if sum(provided) > 1:
            raise ValueError(
                "Only one of page_id, section_id, script_block_id, or page can be provided at a time"
            )
        return self


class RetrieveObservation(SchemaModel):
    """Observation output from RetrieveTool."""

    content: dict[str, Any] = Field(..., description="Retrieved content as dict")
    source: Literal["page", "section", "script_block"] = Field(..., description="Content source type")


def _retrieved_item_to_content_dict(item: RetrievedContextItem) -> dict[str, Any]:
    """Convert a RetrievedContextItem to a dict for observation content."""
    return {
        "source": item.source,
        "source_id": item.source_id,
        "title": item.title,
        "text": item.text,
        "section_id": item.section_id,
        "page": item.page,
        "score": item.score,
    }


class RetrieveTool:
    """
    Precise content retrieval tool.

    Performs exact lookups of lesson content without semantic search.
    Delegates to ContentGetter for actual retrieval.
    """

    def __init__(self, content_getter: ContentGetter):
        """
        Initialize RetrieveTool.

        Args:
            content_getter: ContentGetter instance for precise content access.
        """
        self._content_getter = content_getter

    def retrieve(self, action: RetrieveAction) -> RetrieveObservation:
        """
        Perform precise content retrieval.

        Args:
            action: RetrieveAction specifying what to retrieve.

        Returns:
            RetrieveObservation with content and source.

        Raises:
            ValueError: If the requested content is not found.
        """
        if action.page_id is not None:
            item = self._content_getter.get_page(action.page_id)
            source = "page"
        elif action.section_id is not None:
            item = self._content_getter.get_section(action.section_id)
            source = "section"
        elif action.script_block_id is not None:
            item = self._content_getter.get_script_block(action.script_block_id)
            source = "script_block"
        elif action.page is not None:
            item = self._content_getter.get_page(action.page)
            source = "page"
        else:
            # This shouldn't happen due to validation, but guards against it
            raise ValueError("No lookup field provided in action")

        if item is None:
            raise ValueError(f"Content not found for {source} with given identifier")

        return RetrieveObservation(
            content=_retrieved_item_to_content_dict(item),
            source=source,
        )

    def retrieve_page_by_id(self, page_id: str) -> RetrieveObservation:
        """Convenience method to retrieve a page by its ID."""
        action = RetrieveAction(page_id=page_id)
        return self.retrieve(action)

    def retrieve_section_by_id(self, section_id: str) -> RetrieveObservation:
        """Convenience method to retrieve a section by its ID."""
        action = RetrieveAction(section_id=section_id)
        return self.retrieve(action)

    def retrieve_script_block_by_id(self, script_block_id: str) -> RetrieveObservation:
        """Convenience method to retrieve a script block by its ID."""
        action = RetrieveAction(script_block_id=script_block_id)
        return self.retrieve(action)

    def retrieve_by_page_number(self, page: int) -> RetrieveObservation:
        """Convenience method to retrieve a page by its 1-based page number."""
        action = RetrieveAction(page=page)
        return self.retrieve(action)
