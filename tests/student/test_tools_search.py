"""
Minimal tests for SearchTool.
"""

from src.schemas import RetrievedContextItem
from src.tools.search import SearchAction, SearchObservation, SearchTool


class MockRetriever:
    """Minimal mock of HybridRetriever for testing."""

    def __init__(self, results=None):
        self._results = results or []

    def retrieve(
        self,
        query,
        top_k=5,
        source_filter=None,
        score_threshold=None,
        prefer_section_id=None,
        prefer_page=None,
        prefer_script_block_id=None,
    ):
        if source_filter is None:
            return self._results
        # Filter by source type
        return [r for r in self._results if r.source in source_filter]

    def retrieve_by_section(self, section_id, top_k=None):
        return self._results


class TestSearchAction:
    """Verify SearchAction is a valid Pydantic model."""

    def test_search_action_defaults(self):
        action = SearchAction(query="test query")
        assert action.query == "test query"
        assert action.top_k == 5
        assert action.section_filter is None
        assert action.page_filter is None
        assert action.prefer_section_id is None
        assert action.prefer_page is None
        assert action.prefer_script_block_id is None
        assert action.include_script is True

    def test_search_action_with_filters(self):
        action = SearchAction(
            query="test",
            top_k=10,
            section_filter="section-1",
            page_filter=3,
            prefer_section_id="section-1",
            prefer_page=3,
            prefer_script_block_id="script-1",
            include_script=False,
        )
        assert action.top_k == 10
        assert action.section_filter == "section-1"
        assert action.page_filter == 3
        assert action.prefer_section_id == "section-1"
        assert action.prefer_page == 3
        assert action.prefer_script_block_id == "script-1"
        assert action.include_script is False


class TestSearchObservation:
    """Verify SearchObservation is a valid Pydantic model."""

    def test_search_observation_empty(self):
        obs = SearchObservation(results=[], total=0)
        assert obs.results == []
        assert obs.total == 0

    def test_search_observation_with_results(self):
        item = RetrievedContextItem(
            source="page",
            source_id="page-1",
            title="Test Page",
            text="Test content",
        )
        obs = SearchObservation(results=[item], total=1)
        assert len(obs.results) == 1
        assert obs.total == 1


class TestSearchTool:
    """Test SearchTool interface."""

    def test_search_returns_observation(self):
        mock = MockRetriever([])
        tool = SearchTool(mock)

        action = SearchAction(query="test query")
        obs = tool.search(action)

        assert isinstance(obs, SearchObservation)
        assert obs.results == []
        assert obs.total == 0

    def test_search_with_results(self):
        item = RetrievedContextItem(
            source="page",
            source_id="page-1",
            title="Test Page",
            text="Test content",
        )
        mock = MockRetriever([item])
        tool = SearchTool(mock)

        action = SearchAction(query="test")
        obs = tool.search(action)

        assert len(obs.results) == 1
        assert obs.total == 1
        assert obs.results[0].source_id == "page-1"

    def test_retrieve_by_section(self):
        item = RetrievedContextItem(
            source="section",
            source_id="section-1",
            title="Test Section",
            text="Section content",
        )
        mock = MockRetriever([item])
        tool = SearchTool(mock)

        obs = tool.retrieve_by_section("section-1")

        assert len(obs.results) == 1
        assert obs.total == 1

    def test_observation_is_serializable(self):
        """Verify SearchObservation can be serialized to dict."""
        item = RetrievedContextItem(
            source="page",
            source_id="page-1",
            title="Test",
            text="Content",
        )
        obs = SearchObservation(results=[item], total=1)

        data = obs.model_dump()
        assert isinstance(data, dict)
        assert "results" in data
        assert "total" in data
        assert data["total"] == 1


class TestSearchToolFilters:
    """Test section_filter, page_filter, and include_script filtering."""

    def _make_page(self, page_id: str, page_num: int, section_id: str) -> RetrievedContextItem:
        return RetrievedContextItem(
            source="page",
            source_id=page_id,
            title=f"Page {page_num}",
            text=f"Content page {page_num}",
            section_id=section_id,
            page=page_num,
        )

    def _make_section(self, section_id: str) -> RetrievedContextItem:
        return RetrievedContextItem(
            source="section",
            source_id=section_id,
            title=f"Section {section_id}",
            text=f"Content of section {section_id}",
            section_id=section_id,
        )

    def _make_script(self, block_id: str, section_id: str) -> RetrievedContextItem:
        return RetrievedContextItem(
            source="script_block",
            source_id=block_id,
            title=f"Script {block_id}",
            text=f"Script content {block_id}",
            section_id=section_id,
        )

    def test_section_filter_filters_by_section_id(self):
        """section_filter should only return results with matching section_id."""
        results = [
            self._make_page("page-1", 1, "section-a"),
            self._make_page("page-2", 2, "section-b"),
            self._make_page("page-3", 3, "section-a"),
            self._make_section("section-a"),
            self._make_section("section-b"),
        ]
        mock = MockRetriever(results)
        tool = SearchTool(mock)

        action = SearchAction(query="test", section_filter="section-a")
        obs = tool.search(action)

        assert obs.total == 3  # 2 pages + 1 section from section-a
        for item in obs.results:
            assert item.section_id == "section-a"

    def test_page_filter_filters_by_page_number(self):
        """page_filter should only return results with matching page number."""
        results = [
            self._make_page("page-1", 1, "section-a"),
            self._make_page("page-2", 2, "section-a"),
            self._make_page("page-3", 3, "section-b"),
            self._make_page("page-4", 1, "section-b"),  # same page number, different section
        ]
        mock = MockRetriever(results)
        tool = SearchTool(mock)

        action = SearchAction(query="test", page_filter=1)
        obs = tool.search(action)

        assert obs.total == 2  # page-1 and page-4 both have page=1
        for item in obs.results:
            assert item.page == 1

    def test_section_and_page_filter_combined(self):
        """section_filter and page_filter should be AND-ed together."""
        results = [
            self._make_page("page-1", 1, "section-a"),
            self._make_page("page-2", 2, "section-a"),
            self._make_page("page-3", 1, "section-b"),
            self._make_page("page-4", 3, "section-a"),  # page=3, not page=2
        ]
        mock = MockRetriever(results)
        tool = SearchTool(mock)

        action = SearchAction(query="test", section_filter="section-a", page_filter=2)
        obs = tool.search(action)

        assert obs.total == 1  # only page-2 (section-a + page=2)
        assert obs.results[0].source_id == "page-2"
        assert obs.results[0].section_id == "section-a"
        assert obs.results[0].page == 2

    def test_include_script_false_excludes_script_blocks(self):
        """include_script=False should exclude script_block source type."""
        results = [
            self._make_page("page-1", 1, "section-a"),
            self._make_script("script-1", "section-a"),
        ]
        mock = MockRetriever(results)
        tool = SearchTool(mock)

        action = SearchAction(query="test", include_script=False)
        obs = tool.search(action)

        assert obs.total == 1
        assert obs.results[0].source == "page"
        assert all(item.source != "script_block" for item in obs.results)

    def test_include_script_true_includes_script_blocks(self):
        """include_script=True should include script_block source type."""
        results = [
            self._make_page("page-1", 1, "section-a"),
            self._make_script("script-1", "section-a"),
        ]
        mock = MockRetriever(results)
        tool = SearchTool(mock)

        action = SearchAction(query="test", include_script=True)
        obs = tool.search(action)

        assert obs.total == 2
        sources = {item.source for item in obs.results}
        assert sources == {"page", "script_block"}

    def test_include_script_with_section_filter(self):
        """include_script=False with section_filter should still filter by section_id."""
        results = [
            self._make_page("page-1", 1, "section-a"),
            self._make_script("script-1", "section-a"),
            self._make_script("script-2", "section-b"),
        ]
        mock = MockRetriever(results)
        tool = SearchTool(mock)

        action = SearchAction(query="test", section_filter="section-a", include_script=False)
        obs = tool.search(action)

        assert obs.total == 1
        assert obs.results[0].source_id == "page-1"
        assert obs.results[0].section_id == "section-a"

    def test_top_k_respected_after_filtering(self):
        """top_k should be applied after filtering."""
        results = [self._make_page(f"page-{i}", i, "section-a") for i in range(1, 11)]
        mock = MockRetriever(results)
        tool = SearchTool(mock)

        action = SearchAction(query="test", top_k=3)
        obs = tool.search(action)

        assert obs.total == 3
        assert len(obs.results) == 3

    def test_filter_no_match_returns_empty(self):
        """When filters don't match any result, return empty."""
        results = [
            self._make_page("page-1", 1, "section-a"),
        ]
        mock = MockRetriever(results)
        tool = SearchTool(mock)

        action = SearchAction(query="test", section_filter="section-z")
        obs = tool.search(action)

        assert obs.total == 0
        assert obs.results == []
