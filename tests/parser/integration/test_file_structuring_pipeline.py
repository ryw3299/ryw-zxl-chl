from src.pipelines.file_structuring_pipeline import run_file_structuring_pipeline
from src.schemas import (
    DocumentUnit,
    InputAsset,
    PageBlock,
    ParsedDocument,
    SectionBlock,
    StructuredLessonContent,
)


def _build_parsed_document(unit_count: int) -> ParsedDocument:
    units = []
    for index in range(1, unit_count + 1):
        units.append(
            DocumentUnit(
                unit_id=f"unit_{index}",
                unit_type="slide",
                index=index,
                title=f"Topic {index}",
                text=f"Topic {index} explains concept {index}.",
                source_ref=f"slide {index}",
                source_asset_id="asset_1",
                metadata={"file_type": "pptx"},
            )
        )

    return ParsedDocument(
        course_id="COURSE_1",
        lesson_id="LESSON_1",
        source_assets=[
            InputAsset(
                asset_id="asset_1",
                file_path="dummy.pptx",
                file_type="pptx",
                file_name="dummy.pptx",
            )
        ],
        units=units,
        parse_instruction="Focus on definitions and examples.",
        knowledge_points=[unit.title for unit in units],
        metadata={"asset_count": 1},
    )


def _build_baseline(parsed_document: ParsedDocument) -> StructuredLessonContent:
    pages = []
    sections = []
    for unit in parsed_document.units:
        section_id = f"sec_{unit.index}"
        sections.append(
            SectionBlock(
                section_id=section_id,
                course_id=parsed_document.course_id,
                lesson_id=parsed_document.lesson_id,
                name=unit.title,
                summary=unit.text,
                page_range=[unit.index],
                key_points=[unit.title],
                knowledge_points=[unit.title],
                source_unit_ids=[unit.unit_id],
                section_type="content",
            )
        )
        pages.append(
            PageBlock(
                page_id=f"page_{unit.index}",
                course_id=parsed_document.course_id,
                lesson_id=parsed_document.lesson_id,
                section_id=section_id,
                page=unit.index,
                title=unit.title,
                content=unit.text,
                summary=unit.text,
                key_points=[unit.title],
                knowledge_points=[unit.title],
                source_unit_ids=[unit.unit_id],
                page_role="content",
                file_id=unit.source_asset_id,
                file_type="pptx",
            )
        )

    return StructuredLessonContent(
        course_id=parsed_document.course_id,
        lesson_id=parsed_document.lesson_id,
        source_asset_ids=["asset_1"],
        lesson_summary="Baseline summary",
        pages=pages,
        sections=sections,
        knowledge_points=[unit.title for unit in parsed_document.units],
        parse_instruction=parsed_document.parse_instruction,
        metadata={"source": "baseline"},
    )


def test_file_structuring_pipeline_single_pass_uses_llm_result():
    parsed_document = _build_parsed_document(unit_count=4)
    baseline = _build_baseline(parsed_document)

    def fake_llm(*, stage, metadata, **_kwargs):
        assert stage == "single_pass"
        units = metadata["parsed_document"]["units"]
        return {
            "lesson_summary": "Single pass summary",
            "pages": [
                {
                    "page": index,
                    "title": unit["title"],
                    "summary": f"Summary for {unit['title']}",
                    "key_points": [unit["title"]],
                    "knowledge_points": [unit["title"]],
                    "source_unit_ids": [unit["unit_id"]],
                    "page_role": "content",
                    "section_id": f"local_sec_{index}",
                }
                for index, unit in enumerate(units, start=1)
            ],
            "sections": [
                {
                    "section_id": f"local_sec_{index}",
                    "name": unit["title"],
                    "summary": f"Section summary for {unit['title']}",
                    "page_range": [index],
                    "key_points": [unit["title"]],
                    "knowledge_points": [unit["title"]],
                    "source_unit_ids": [unit["unit_id"]],
                    "section_type": "content",
                }
                for index, unit in enumerate(units, start=1)
            ],
            "knowledge_points": [unit["title"] for unit in units],
        }

    result = run_file_structuring_pipeline(
        parsed_document=parsed_document,
        baseline_structured_content=baseline,
        llm_callable=fake_llm,
    )

    assert result["used_fallback"] is False
    assert result["strategy"] == "single_pass"
    assert result["structured_content"].lesson_summary == "Single pass summary"
    assert result["structured_content"].pages[0].source_unit_ids == ["unit_1"]
    assert result["structured_content"].sections[0].section_id == "sec_1"


def test_file_structuring_pipeline_chunked_merges_local_results():
    parsed_document = _build_parsed_document(unit_count=10)
    baseline = _build_baseline(parsed_document)

    def fake_llm(*, stage, metadata, **_kwargs):
        assert stage == "local_chunk"
        chunk_units = metadata["chunk_units"]
        first = chunk_units[0]
        last = chunk_units[-1]
        return {
            "lesson_summary": f"Chunk {metadata['chunk_index']} summary",
            "pages": [
                {
                    "page": offset,
                    "title": unit["title"],
                    "summary": f"Summary for {unit['title']}",
                    "key_points": [unit["title"]],
                    "knowledge_points": [unit["title"]],
                    "source_unit_ids": [unit["unit_id"]],
                    "page_role": "content",
                    "section_id": f"chunk_sec_{metadata['chunk_index']}",
                }
                for offset, unit in enumerate(chunk_units, start=1)
            ],
            "sections": [
                {
                    "section_id": f"chunk_sec_{metadata['chunk_index']}",
                    "name": f"{first['title']} to {last['title']}",
                    "summary": f"Chunk {metadata['chunk_index']} covers nearby content.",
                    "page_range": list(range(1, len(chunk_units) + 1)),
                    "key_points": [first["title"], last["title"]],
                    "knowledge_points": [first["title"], last["title"]],
                    "source_unit_ids": [unit["unit_id"] for unit in chunk_units],
                    "section_type": "content",
                }
            ],
            "knowledge_points": [unit["title"] for unit in chunk_units],
        }

    result = run_file_structuring_pipeline(
        parsed_document=parsed_document,
        baseline_structured_content=baseline,
        llm_callable=fake_llm,
    )

    assert result["used_fallback"] is False
    assert result["strategy"] == "chunked"
    assert result["chunk_count"] == 2
    assert len(result["structured_content"].pages) == 10
    assert len(result["structured_content"].sections) == 2
    assert result["structured_content"].sections[0].source_unit_ids[0] == "unit_1"
    assert result["structured_content"].sections[1].source_unit_ids[0] == "unit_7"


def test_file_structuring_pipeline_falls_back_without_llm():
    parsed_document = _build_parsed_document(unit_count=10)
    baseline = _build_baseline(parsed_document)

    result = run_file_structuring_pipeline(
        parsed_document=parsed_document,
        baseline_structured_content=baseline,
        llm_callable=None,
    )

    assert result["used_fallback"] is True
    assert result["strategy"] == "chunked"
    assert result["structured_content"].lesson_summary == "Baseline summary"
    assert result["validation_errors"]


def test_file_structuring_pipeline_coerces_local_structured_summary_shape():
    parsed_document = _build_parsed_document(unit_count=10)
    baseline = _build_baseline(parsed_document)

    def fake_llm(*, stage, metadata, **_kwargs):
        assert stage == "local_chunk"
        chunk_units = metadata["chunk_units"]
        return {
            "local_structured_summary": [
                {
                    "section_title": f"{chunk_units[0]['title']} cluster",
                    "summary": "Local structured summary returned in a non-standard wrapper.",
                    "source_unit_ids": [unit["unit_id"] for unit in chunk_units],
                }
            ]
        }

    result = run_file_structuring_pipeline(
        parsed_document=parsed_document,
        baseline_structured_content=baseline,
        llm_callable=fake_llm,
    )

    assert result["used_fallback"] is False
    assert result["strategy"] == "chunked"
    assert len(result["structured_content"].pages) == 10
    assert len(result["structured_content"].sections) == 2
    assert result["structured_content"].metadata["normalized"] is True


def test_file_structuring_pipeline_normalizes_loose_schema_fields():
    parsed_document = _build_parsed_document(unit_count=10)
    baseline = _build_baseline(parsed_document)

    def fake_llm(*, stage, metadata, **_kwargs):
        assert stage == "local_chunk"
        chunk_units = metadata["chunk_units"]
        return {
            "lesson_summary": "Loose schema response",
            "pages": [
                {
                    "page_id": f"page_{offset}",
                    "title": unit["title"],
                    "summary": f"Summary for {unit['title']}",
                    "key_points": [{"name": unit["title"]}],
                    "knowledge_points": [{"title": unit["title"]}],
                    "source_unit_ids": [unit["unit_id"]],
                    "page_role": "content",
                    "section_id": "",
                }
                for offset, unit in enumerate(chunk_units, start=1)
            ],
            "sections": [
                {
                    "name": f"{chunk_units[0]['title']} cluster",
                    "summary": "Nearby units grouped together.",
                    "source_unit_ids": [unit["unit_id"] for unit in chunk_units],
                    "page_id": "page_1",
                }
            ],
            "knowledge_points": [{"knowledge_point": unit["title"]} for unit in chunk_units],
        }

    result = run_file_structuring_pipeline(
        parsed_document=parsed_document,
        baseline_structured_content=baseline,
        llm_callable=fake_llm,
    )

    assert result["used_fallback"] is False
    assert result["strategy"] == "chunked"
    assert result["structured_content"].sections[0].section_id == "sec_1"
    assert result["structured_content"].pages[0].page == 1
    assert isinstance(result["structured_content"].knowledge_points[0], str)


def test_file_structuring_pipeline_rebuilds_sections_from_final_pages():
    parsed_document = _build_parsed_document(unit_count=4)
    baseline = _build_baseline(parsed_document)

    def fake_llm(*, stage, metadata, **_kwargs):
        assert stage == "single_pass"
        units = metadata["parsed_document"]["units"]
        return {
            "lesson_summary": "Rebuilt sections",
            "pages": [
                {
                    "page": 1,
                    "title": units[0]["title"],
                    "summary": "Page 1",
                    "key_points": [units[0]["title"]],
                    "knowledge_points": [units[0]["title"]],
                    "source_unit_ids": [units[0]["unit_id"]],
                    "page_role": "content",
                    "section_id": "alpha",
                },
                {
                    "page": 2,
                    "title": units[1]["title"],
                    "summary": "Page 2",
                    "key_points": [units[1]["title"]],
                    "knowledge_points": [units[1]["title"]],
                    "source_unit_ids": [units[1]["unit_id"]],
                    "page_role": "content",
                    "section_id": "beta",
                },
                {
                    "page": 3,
                    "title": units[2]["title"],
                    "summary": "Page 3",
                    "key_points": [units[2]["title"]],
                    "knowledge_points": [units[2]["title"]],
                    "source_unit_ids": [units[2]["unit_id"]],
                    "page_role": "content",
                    "section_id": "alpha",
                },
            ],
            "sections": [
                {
                    "section_id": "alpha",
                    "name": "Alpha Section",
                    "summary": "Alpha summary",
                    "page_range": [1, 3],
                    "key_points": ["Alpha"],
                    "knowledge_points": ["Alpha"],
                    "source_unit_ids": [units[0]["unit_id"], units[2]["unit_id"]],
                    "section_type": "content",
                },
                {
                    "section_id": "beta",
                    "name": "Beta Section",
                    "summary": "Beta summary",
                    "page_range": [2],
                    "key_points": ["Beta"],
                    "knowledge_points": ["Beta"],
                    "source_unit_ids": [units[1]["unit_id"]],
                    "section_type": "content",
                },
                {
                    "section_id": "orphan",
                    "name": "Orphan Section",
                    "summary": "Should be dropped",
                    "page_range": [4],
                    "key_points": ["Orphan"],
                    "knowledge_points": ["Orphan"],
                    "source_unit_ids": [units[3]["unit_id"]],
                    "section_type": "content",
                },
            ],
            "knowledge_points": ["Alpha", "Beta"],
        }

    result = run_file_structuring_pipeline(
        parsed_document=parsed_document,
        baseline_structured_content=baseline,
        llm_callable=fake_llm,
    )

    assert result["used_fallback"] is False
    assert len(result["structured_content"].pages) == 3
    assert len(result["structured_content"].sections) == 3
    assert [page.section_id for page in result["structured_content"].pages] == ["sec_1", "sec_2", "sec_3"]
    assert [section.page_range for section in result["structured_content"].sections] == [[1], [2], [3]]
