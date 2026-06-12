"""
Minimal tests for RetrieveTool.
"""

import pytest

from src.schemas.common import PageBlock, ScriptBlock, SectionBlock, StructuredLessonContent
from src.schemas.generate_schemas import LessonScript
from src.tools import RetrieveAction, RetrieveObservation, RetrieveTool
from src.utils.student import ContentGetter


class TestRetrieveAction:
    """Tests for RetrieveAction validation."""

    def test_requires_exactly_one_field(self):
        """Must provide exactly one field."""
        with pytest.raises(ValueError, match="Exactly one"):
            RetrieveAction()

    def test_rejects_multiple_fields(self):
        """Cannot provide more than one field."""
        with pytest.raises(ValueError, match="Only one"):
            RetrieveAction(page_id="p1", section_id="s1")

    def test_accepts_page_id_only(self):
        """page_id alone is valid."""
        action = RetrieveAction(page_id="page_1")
        assert action.page_id == "page_1"
        assert action.section_id is None
        assert action.script_block_id is None
        assert action.page is None

    def test_accepts_section_id_only(self):
        """section_id alone is valid."""
        action = RetrieveAction(section_id="section_1")
        assert action.section_id == "section_1"

    def test_accepts_script_block_id_only(self):
        """script_block_id alone is valid."""
        action = RetrieveAction(script_block_id="script_1")
        assert action.script_block_id == "script_1"

    def test_accepts_page_only(self):
        """page number alone is valid."""
        action = RetrieveAction(page=5)
        assert action.page == 5


class TestRetrieveTool:
    """Tests for RetrieveTool retrieval operations."""

    @pytest.fixture
    def content_getter(self):
        """Create a ContentGetter with test data."""
        page1 = PageBlock(
            page_id="page_1",
            course_id="course_1",
            lesson_id="lesson_1",
            section_id="section_1",
            page=1,
            title="Page One",
            content="Content of page one",
            key_points=["point1"],
        )
        page2 = PageBlock(
            page_id="page_2",
            course_id="course_1",
            lesson_id="lesson_1",
            section_id="section_1",
            page=2,
            title="Page Two",
            content="Content of page two",
            key_points=["point2"],
        )
        section1 = SectionBlock(
            section_id="section_1",
            course_id="course_1",
            lesson_id="lesson_1",
            name="Section One",
            summary="Summary of section one",
            page_range=[1, 2],
            key_points=["key1"],
        )
        script1 = ScriptBlock(
            script_block_id="script_1",
            course_id="course_1",
            lesson_id="lesson_1",
            section_id="section_1",
            title="Script One",
            script_text="Script content one",
            page_range=[1],
            key_points=["script_point"],
        )
        structured_content = StructuredLessonContent(
            course_id="course_1",
            lesson_id="lesson_1",
            pages=[page1, page2],
            sections=[section1],
        )
        lesson_script = LessonScript(
            lesson_title="Test Lesson",
            script_blocks=[script1],
            metadata={"lesson_id": "lesson_1"},
        )
        return ContentGetter(
            structured_content=structured_content,
            lesson_script=lesson_script,
        )

    @pytest.fixture
    def retrieve_tool(self, content_getter):
        """Create a RetrieveTool with test data."""
        return RetrieveTool(content_getter)

    def test_retrieve_page_by_id(self, retrieve_tool):
        """Retrieve a page by its ID."""
        action = RetrieveAction(page_id="page_1")
        obs = retrieve_tool.retrieve(action)

        assert isinstance(obs, RetrieveObservation)
        assert obs.source == "page"
        assert obs.content["source_id"] == "page_1"
        assert obs.content["title"] == "Page One"

    def test_retrieve_section_by_id(self, retrieve_tool):
        """Retrieve a section by its ID."""
        action = RetrieveAction(section_id="section_1")
        obs = retrieve_tool.retrieve(action)

        assert obs.source == "section"
        assert obs.content["source_id"] == "section_1"
        assert obs.content["title"] == "Section One"

    def test_retrieve_script_block_by_id(self, retrieve_tool):
        """Retrieve a script block by its ID."""
        action = RetrieveAction(script_block_id="script_1")
        obs = retrieve_tool.retrieve(action)

        assert obs.source == "script_block"
        assert obs.content["source_id"] == "script_1"
        assert obs.content["title"] == "Script One"

    def test_retrieve_by_page_number(self, retrieve_tool):
        """Retrieve a page by its 1-based page number."""
        action = RetrieveAction(page=1)
        obs = retrieve_tool.retrieve(action)

        assert obs.source == "page"
        assert obs.content["page"] == 1

    def test_retrieve_not_found_raises(self, retrieve_tool):
        """Non-existent content raises ValueError."""
        action = RetrieveAction(page_id="nonexistent")
        with pytest.raises(ValueError, match="not found"):
            retrieve_tool.retrieve(action)

    def test_convenience_method_page_by_id(self, retrieve_tool):
        """Test retrieve_page_by_id convenience method."""
        obs = retrieve_tool.retrieve_page_by_id("page_1")
        assert obs.source == "page"

    def test_convenience_method_section_by_id(self, retrieve_tool):
        """Test retrieve_section_by_id convenience method."""
        obs = retrieve_tool.retrieve_section_by_id("section_1")
        assert obs.source == "section"

    def test_convenience_method_script_block_by_id(self, retrieve_tool):
        """Test retrieve_script_block_by_id convenience method."""
        obs = retrieve_tool.retrieve_script_block_by_id("script_1")
        assert obs.source == "script_block"

    def test_convenience_method_by_page_number(self, retrieve_tool):
        """Test retrieve_by_page_number convenience method."""
        obs = retrieve_tool.retrieve_by_page_number(1)
        assert obs.source == "page"
        assert obs.content["page"] == 1
