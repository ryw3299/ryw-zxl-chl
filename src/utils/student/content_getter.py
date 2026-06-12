"""
ContentGetter module for precise content retrieval.

Provides exact lookup of content from structured lesson data
without semantic/embedding-based search.
"""

from typing import Optional, Union

from src.schemas import RetrievedContextItem
from src.schemas.common import PageBlock, ScriptBlock, SectionBlock, StructuredLessonContent
from src.schemas.generate_schemas import LessonScript

from .helpers import (
    extract_page_content,
    extract_script_content,
    extract_section_content,
    map_to_retrieved_context_item,
)


class ContentGetter:
    """
    Precise content getter for lesson content.

    Provides exact lookup of pages, sections, and script blocks
    by their identifiers. Does NOT perform semantic search.
    """

    def __init__(
        self,
        structured_content: Optional[StructuredLessonContent] = None,
        lesson_script: Optional[LessonScript] = None,
    ):
        """
        Initialize the ContentGetter.

        Args:
            structured_content: Structured lesson content for page/section lookup
            lesson_script: Lesson script for script block lookup
        """
        self._structured_content = structured_content
        self._lesson_script = lesson_script
        self._page_index: dict[str, PageBlock] = {}
        self._section_index: dict[str, SectionBlock] = {}
        self._script_index: dict[str, ScriptBlock] = {}
        self._build_indices()

    def _build_indices(self) -> None:
        """Build lookup indices for fast access."""
        if self._structured_content is not None:
            for page in self._structured_content.pages:
                if page.page_id:
                    self._page_index[page.page_id] = page
                self._page_index[str(page.page)] = page

            for section in self._structured_content.sections:
                self._section_index[section.section_id] = section

        if self._lesson_script is not None:
            for block in self._lesson_script.script_blocks:
                if block.script_block_id:
                    self._script_index[block.script_block_id] = block

    def get_page(self, page_id: Union[str, int]) -> Optional[RetrievedContextItem]:
        """
        Get a page by its ID or page number.

        Args:
            page_id: Page ID string or 1-based page number

        Returns:
            RetrievedContextItem if found, None otherwise
        """
        page = self._page_index.get(str(page_id))
        if page is None:
            return None

        text = extract_page_content(page)
        return map_to_retrieved_context_item(
            source_type="page",
            source_id=str(page.page_id or page.page),
            title=page.title,
            text=text,
            section_id=page.section_id,
            page=page.page,
            score=1.0,  # Exact match has perfect score
        )

    def get_section(self, section_id: str) -> Optional[RetrievedContextItem]:
        """
        Get a section by its ID.

        Args:
            section_id: Section identifier

        Returns:
            RetrievedContextItem if found, None otherwise
        """
        section = self._section_index.get(section_id)
        if section is None:
            return None

        text = extract_section_content(section)
        page = section.page_range[0] if section.page_range else None
        return map_to_retrieved_context_item(
            source_type="section",
            source_id=section.section_id,
            title=section.name,
            text=text,
            section_id=section_id,
            page=page,
            score=1.0,
        )

    def get_script_block(self, script_block_id: str) -> Optional[RetrievedContextItem]:
        """
        Get a script block by its ID.

        Args:
            script_block_id: Script block identifier

        Returns:
            RetrievedContextItem if found, None otherwise
        """
        script = self._script_index.get(script_block_id)
        if script is None:
            return None

        text = extract_script_content(script)
        page = script.page_range[0] if script.page_range else None
        return map_to_retrieved_context_item(
            source_type="script_block",
            source_id=script_block_id,
            title=script.title,
            text=text,
            section_id=script.section_id,
            page=page,
            score=1.0,
        )

    def get_source(
        self,
        source_type: str,
        source_id: Union[str, int],
    ) -> Optional[RetrievedContextItem]:
        """
        Get a source by type and identifier.

        This is a small convenience layer for chunk-based retrieval flows that
        still need to fetch the full parent source body.
        """
        if source_type == "page":
            return self.get_page(source_id)
        if source_type == "section":
            return self.get_section(str(source_id))
        if source_type == "script_block":
            return self.get_script_block(str(source_id))
        raise ValueError(f"Unsupported source_type: {source_type}")

    def get_pages_in_section(self, section_id: str) -> list[RetrievedContextItem]:
        """
        Get all pages within a section.

        Args:
            section_id: Section identifier

        Returns:
            List of RetrievedContextItem for pages in the section
        """
        if self._structured_content is None:
            return []

        results = []
        for page in self._structured_content.pages:
            if page.section_id == section_id:
                text = extract_page_content(page)
                item = map_to_retrieved_context_item(
                    source_type="page",
                    source_id=str(page.page_id or page.page),
                    title=page.title,
                    text=text,
                    section_id=page.section_id,
                    page=page.page,
                    score=1.0,
                )
                results.append(item)

        return results

    def get_sections_in_page(self, page: int) -> list[RetrievedContextItem]:
        """
        Get all sections that contain a specific page.

        Args:
            page: 1-based page number

        Returns:
            List of RetrievedContextItem for sections containing the page
        """
        if self._structured_content is None:
            return []

        results = []
        for section in self._structured_content.sections:
            if page in section.page_range:
                text = extract_section_content(section)
                item = map_to_retrieved_context_item(
                    source_type="section",
                    source_id=section.section_id,
                    title=section.name,
                    text=text,
                    section_id=section.section_id,
                    page=section.page_range[0] if section.page_range else None,
                    score=1.0,
                )
                results.append(item)

        return results

    def get_script_blocks_in_section(self, section_id: str) -> list[RetrievedContextItem]:
        """
        Get all script blocks within a section.

        Args:
            section_id: Section identifier

        Returns:
            List of RetrievedContextItem for script blocks in the section
        """
        if self._lesson_script is None:
            return []

        results = []
        for script in self._lesson_script.script_blocks:
            if script.section_id == section_id:
                text = extract_script_content(script)
                item = map_to_retrieved_context_item(
                    source_type="script_block",
                    source_id=script.script_block_id or "",
                    title=script.title,
                    text=text,
                    section_id=script.section_id,
                    page=script.page_range[0] if script.page_range else None,
                    score=1.0,
                )
                results.append(item)

        return results

    def get_all_pages(self) -> list[RetrievedContextItem]:
        """
        Get all pages as RetrievedContextItem list.

        Returns:
            List of all pages
        """
        if self._structured_content is None:
            return []

        items: list[RetrievedContextItem] = []
        for page in self._structured_content.pages:
            item = self.get_page(str(page.page_id or page.page))
            if item is not None:
                items.append(item)
        return items

    def get_all_sections(self) -> list[RetrievedContextItem]:
        """
        Get all sections as RetrievedContextItem list.

        Returns:
            List of all sections
        """
        if self._structured_content is None:
            return []

        items: list[RetrievedContextItem] = []
        for section in self._structured_content.sections:
            item = self.get_section(section.section_id)
            if item is not None:
                items.append(item)
        return items

    def get_all_script_blocks(self) -> list[RetrievedContextItem]:
        """
        Get all script blocks as RetrievedContextItem list.

        Returns:
            List of all script blocks
        """
        if self._lesson_script is None:
            return []

        items: list[RetrievedContextItem] = []
        for block in self._lesson_script.script_blocks:
            item = self.get_script_block(block.script_block_id or "")
            if item is not None:
                items.append(item)
        return items
