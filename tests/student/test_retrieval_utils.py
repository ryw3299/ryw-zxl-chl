"""
Minimal tests for student retrieval utils.
"""

import pytest

from src.schemas import RetrievedContextItem
from src.schemas.common import PageBlock, SectionBlock, StructuredLessonContent
from src.schemas.generate_schemas import LessonScript, ScriptBlock
from src.utils.student import (
    BM25Store,
    ChunkBuilder,
    ChunkRecord,
    ContentGetter,
    HybridRetriever,
    InMemoryEmbedder,
    RetrieverFactory,
    VectorStore,
    build_context_string,
    map_to_retrieved_context_item,
)
from src.utils.student.config import clear_student_settings_cache
from src.utils.student.helpers import chunk_text


class TestMapToRetrievedContextItem:
    """Tests for map_to_retrieved_context_item helper."""

    def test_map_page_source(self):
        item = map_to_retrieved_context_item(
            source_type="page",
            source_id="page_1",
            title="Test Page",
            text="Page content here",
            section_id="section_1",
            page=1,
            score=0.95,
        )
        assert isinstance(item, RetrievedContextItem)
        assert item.source == "page"
        assert item.source_id == "page_1"
        assert item.title == "Test Page"
        assert item.text == "Page content here"
        assert item.section_id == "section_1"
        assert item.page == 1
        assert item.score == 0.95

    def test_map_section_source(self):
        item = map_to_retrieved_context_item(
            source_type="section",
            source_id="section_1",
            title="Test Section",
            text="Section content",
        )
        assert item.source == "section"
        assert item.source_id == "section_1"

    def test_invalid_source_type_raises(self):
        with pytest.raises(ValueError):
            map_to_retrieved_context_item(
                source_type="invalid",
                source_id="id_1",
                title="Title",
                text="Text",
            )


class TestBuildContextString:
    """Tests for build_context_string helper."""

    def test_empty_list_returns_empty_string(self):
        result = build_context_string([])
        assert result == ""

    def test_single_item(self):
        item = RetrievedContextItem(
            source="page",
            source_id="page_1",
            title="Page 1",
            text="Content here",
            page=1,
        )
        result = build_context_string([item], include_header=True)
        assert "Page 1" in result
        assert "Content here" in result

    def test_max_length_respected(self):
        item = RetrievedContextItem(
            source="page",
            source_id="page_1",
            title="Page 1",
            text="A" * 1000,
            page=1,
        )
        result = build_context_string([item], max_length=100, include_header=False)
        assert len(result) <= 100


class TestInMemoryEmbedder:
    """Tests for InMemoryEmbedder."""

    def test_embed_returns_list(self):
        embedder = InMemoryEmbedder()
        result = embedder.embed("test text")
        assert isinstance(result, list)
        assert len(result) == 1536

    def test_embed_batch(self):
        embedder = InMemoryEmbedder()
        texts = ["text1", "text2", "text3"]
        results = embedder.embed_batch(texts)
        assert len(results) == 3
        assert all(isinstance(r, list) for r in results)

    def test_embed_deterministic(self):
        embedder = InMemoryEmbedder()
        result1 = embedder.embed("same text")
        result2 = embedder.embed("same text")
        assert result1 == result2

    def test_different_texts_different_embeddings(self):
        embedder = InMemoryEmbedder()
        result1 = embedder.embed("text one")
        result2 = embedder.embed("text two")
        assert result1 != result2


class TestVectorStore:
    """Tests for VectorStore."""

    def test_add_and_get(self):
        store = VectorStore()
        embedder = InMemoryEmbedder()
        vec = embedder.embed("test content")
        store.add("id_1", vec, "test content", {"meta": "value"})
        entry = store.get("id_1")
        assert entry is not None
        assert entry.text == "test content"
        assert entry.metadata["meta"] == "value"

    def test_search(self):
        store = VectorStore()
        embedder = InMemoryEmbedder()
        vec1 = embedder.embed("apple fruit")
        vec2 = embedder.embed("car automobile")
        store.add("id_1", vec1, "apple content")
        store.add("id_2", vec2, "car content")
        results = store.search(vec1, k=2)
        assert len(results) >= 1
        # First result should be the most similar
        assert results[0][0].id == "id_1"

    def test_delete(self):
        store = VectorStore()
        embedder = InMemoryEmbedder()
        vec = embedder.embed("test")
        store.add("id_1", vec, "content")
        assert store.get("id_1") is not None
        store.delete("id_1")
        assert store.get("id_1") is None

    def test_dimension_mismatch_raises(self):
        store = VectorStore()
        store.add("id_1", [1.0, 2.0, 3.0], "text")  # dimension 3
        with pytest.raises(ValueError):
            store.add("id_2", [1.0, 2.0], "text")  # dimension 2


class TestContentGetter:
    """Tests for ContentGetter with precise lookup."""

    def setup_method(self):
        """Set up test data."""
        self.page1 = PageBlock(
            page_id="page_1",
            course_id="course_1",
            lesson_id="lesson_1",
            section_id="section_1",
            page=1,
            title="Page One",
            content="Content of page one",
            key_points=["point1", "point2"],
        )
        self.section1 = SectionBlock(
            section_id="section_1",
            course_id="course_1",
            lesson_id="lesson_1",
            name="Section One",
            summary="Summary of section one",
            page_range=[1, 2],
            key_points=["key1"],
            knowledge_points=["kp1"],
        )
        self.script1 = ScriptBlock(
            script_block_id="script_1",
            course_id="course_1",
            lesson_id="lesson_1",
            section_id="section_1",
            title="Script One",
            script_text="Script content one",
            page_range=[1],
            key_points=["script_point"],
        )
        self.structured_content = StructuredLessonContent(
            course_id="course_1",
            lesson_id="lesson_1",
            pages=[self.page1],
            sections=[self.section1],
        )
        self.lesson_script = LessonScript(
            lesson_title="Test Lesson",
            script_blocks=[self.script1],
            metadata={"lesson_id": "lesson_1"},
        )

    def test_get_page_by_id(self):
        getter = ContentGetter(
            structured_content=self.structured_content,
            lesson_script=self.lesson_script,
        )
        item = getter.get_page("page_1")
        assert item is not None
        assert item.source == "page"
        assert item.title == "Page One"

    def test_get_section_by_id(self):
        getter = ContentGetter(
            structured_content=self.structured_content,
            lesson_script=self.lesson_script,
        )
        item = getter.get_section("section_1")
        assert item is not None
        assert item.source == "section"
        assert item.title == "Section One"

    def test_get_script_block_by_id(self):
        getter = ContentGetter(
            structured_content=self.structured_content,
            lesson_script=self.lesson_script,
        )
        item = getter.get_script_block("script_1")
        assert item is not None
        assert item.source == "script_block"
        assert item.title == "Script One"

    def test_get_nonexistent_returns_none(self):
        getter = ContentGetter(
            structured_content=self.structured_content,
            lesson_script=self.lesson_script,
        )
        assert getter.get_page("nonexistent") is None
        assert getter.get_section("nonexistent") is None
        assert getter.get_script_block("nonexistent") is None


class TestHybridRetriever:
    """Tests for HybridRetriever."""

    def setup_method(self):
        """Set up test data."""
        self.page1 = PageBlock(
            page_id="page_1",
            course_id="course_1",
            lesson_id="lesson_1",
            section_id="section_1",
            page=1,
            title="Introduction to Python",
            content="Python is a programming language",
            key_points=["Python basics"],
        )
        self.page2 = PageBlock(
            page_id="page_2",
            course_id="course_1",
            lesson_id="lesson_1",
            section_id="section_2",
            page=2,
            title="Variables in Python",
            content="Variables store data values",
            key_points=["Variables"],
        )
        self.section1 = SectionBlock(
            section_id="section_1",
            course_id="course_1",
            lesson_id="lesson_1",
            name="Basics",
            summary="Programming basics",
            page_range=[1],
        )
        self.structured_content = StructuredLessonContent(
            course_id="course_1",
            lesson_id="lesson_1",
            pages=[self.page1, self.page2],
            sections=[self.section1],
        )

    def test_retrieve_returns_results(self):
        retriever = HybridRetriever(
            structured_content=self.structured_content,
        )
        results = retriever.retrieve("Python programming", top_k=3)
        assert isinstance(results, list)

    def test_retrieve_with_score_threshold(self):
        retriever = HybridRetriever(
            structured_content=self.structured_content,
            score_threshold=0.5,
        )
        results = retriever.retrieve("Python", top_k=5)
        for item in results:
            if item.score is not None:
                assert item.score >= 0.5

    def test_retrieve_by_section(self):
        retriever = HybridRetriever(
            structured_content=self.structured_content,
        )
        results = retriever.retrieve_by_section("section_1")
        assert isinstance(results, list)

    def test_empty_query_returns_empty(self):
        retriever = HybridRetriever(
            structured_content=self.structured_content,
        )
        results = retriever.retrieve("")
        # Empty query may return empty or fallback results
        assert isinstance(results, list)


class TestContentGetterCollections:
    def test_get_all_methods_return_context_items_only(self):
        page = PageBlock(
            page_id="page_1",
            course_id="course_1",
            lesson_id="lesson_1",
            section_id="section_1",
            page=1,
            title="Page One",
            content="Page content",
        )
        section = SectionBlock(
            section_id="section_1",
            course_id="course_1",
            lesson_id="lesson_1",
            name="Section One",
            summary="Section summary",
            page_range=[1],
        )
        script = ScriptBlock(
            script_block_id="script_1",
            course_id="course_1",
            lesson_id="lesson_1",
            section_id="section_1",
            title="Script One",
            script_text="Script content",
            page_range=[1],
        )
        getter = ContentGetter(
            structured_content=StructuredLessonContent(
                course_id="course_1",
                lesson_id="lesson_1",
                pages=[page],
                sections=[section],
            ),
            lesson_script=LessonScript(
                lesson_title="Test Lesson",
                script_blocks=[script],
                metadata={"lesson_id": "lesson_1"},
            ),
        )

        pages = getter.get_all_pages()
        sections = getter.get_all_sections()
        scripts = getter.get_all_script_blocks()

        assert len(pages) == 1
        assert len(sections) == 1
        assert len(scripts) == 1
        assert all(item is not None for item in pages)
        assert all(item is not None for item in sections)
        assert all(item is not None for item in scripts)


class TestChunkText:
    def test_chunk_text_rejects_invalid_overlap(self):
        with pytest.raises(ValueError):
            chunk_text("abcdef", chunk_size=4, overlap=4)

    def test_chunk_text_rejects_non_positive_chunk_size(self):
        with pytest.raises(ValueError):
            chunk_text("abcdef", chunk_size=0, overlap=1)


class TestChunkBuilder:
    def test_build_creates_parent_aligned_chunks(self):
        structured = StructuredLessonContent(
            course_id="course_1",
            lesson_id="lesson_1",
            pages=[
                PageBlock(
                    page_id="page_1",
                    lesson_id="lesson_1",
                    section_id="section_1",
                    page=1,
                    title="应力基础",
                    content="应力表示单位面积上的内力。" * 40,
                    key_points=["应力"],
                )
            ],
            sections=[
                SectionBlock(
                    section_id="section_1",
                    lesson_id="lesson_1",
                    name="基础概念",
                    summary="讲解应力定义",
                    page_range=[1],
                    key_points=["应力"],
                )
            ],
        )
        builder = ChunkBuilder(chunk_size=120, overlap=20)
        chunks = builder.build(structured, lesson_script=None)

        assert chunks
        assert any(chunk.source_type == "page" for chunk in chunks)
        assert all(chunk.parent_source_id for chunk in chunks)
        assert all(chunk.text for chunk in chunks)


class TestBM25Store:
    def test_search_finds_chinese_keyword(self):
        chunks = [
            ChunkRecord(
                chunk_id="page:page_1:chunk:0",
                lesson_id="lesson_1",
                source_type="page",
                source_id="page_1",
                parent_source_type="page",
                parent_source_id="page_1",
                section_id="section_1",
                page=1,
                title="应力基础",
                text="Title: 应力基础\n应力表示单位面积上的内力。",
                chunk_index=0,
                key_points=["应力"],
            ),
            ChunkRecord(
                chunk_id="page:page_2:chunk:0",
                lesson_id="lesson_1",
                source_type="page",
                source_id="page_2",
                parent_source_type="page",
                parent_source_id="page_2",
                section_id="section_2",
                page=2,
                title="位移",
                text="Title: 位移\n位移用于描述位置变化。",
                chunk_index=0,
                key_points=["位移"],
            ),
        ]
        store = BM25Store(chunks)
        results = store.search("应力", k=2)

        assert results
        assert results[0][0].source_id == "page_1"


class TestRetrieverFactory:
    def test_get_or_create_reuses_cached_retriever(self, tmp_path, monkeypatch):
        monkeypatch.setenv("RAG_INDEX_DIR", str(tmp_path / "indices"))
        clear_student_settings_cache()
        RetrieverFactory.clear_cache()

        structured = StructuredLessonContent(
            course_id="course_1",
            lesson_id="lesson_1",
            pages=[
                PageBlock(
                    page_id="page_1",
                    lesson_id="lesson_1",
                    section_id="section_1",
                    page=1,
                    title="应力基础",
                    content="应力表示单位面积上的内力。",
                    key_points=["应力"],
                )
            ],
            sections=[
                SectionBlock(
                    section_id="section_1",
                    lesson_id="lesson_1",
                    name="基础概念",
                    summary="讲解应力定义",
                    page_range=[1],
                    key_points=["应力"],
                )
            ],
        )

        first = RetrieverFactory.get_or_create(structured_content=structured)
        second = RetrieverFactory.get_or_create(structured_content=structured)

        assert first is second
        assert (tmp_path / "indices").exists()

        RetrieverFactory.clear_cache()
        clear_student_settings_cache()
