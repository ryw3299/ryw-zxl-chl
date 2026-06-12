from src.pipelines.generate_pipeline import _build_section_payload, run_generate_pipeline
from src.schemas import GenerateInput, PageBlock, SectionBlock, StructuredLessonContent


def _build_generate_input() -> GenerateInput:
    pages = [
        PageBlock(
            page_id="page_1",
            course_id="COURSE_GEN",
            lesson_id="LESSON_GEN",
            section_id="sec_1",
            page=1,
            title="控制系统数学模型",
            content="介绍数学模型的基本作用。",
            summary="介绍数学模型的作用与范围。",
            key_points=["数学模型的作用", "课程内容概览"],
            knowledge_points=["数学模型", "课程概览"],
            source_unit_ids=["unit_1"],
            page_role="cover",
            file_id="asset_1",
            file_type="pptx",
        ),
        PageBlock(
            page_id="page_2",
            course_id="COURSE_GEN",
            lesson_id="LESSON_GEN",
            section_id="sec_2",
            page=2,
            title="微分方程建模",
            content="说明输入输出微分方程的建立思路。",
            summary="说明建模步骤与核心思路。",
            key_points=["确定输入输出", "整理标准形式"],
            knowledge_points=["微分方程建模", "输入输出"],
            source_unit_ids=["unit_2"],
            page_role="content",
            file_id="asset_1",
            file_type="pptx",
        ),
    ]
    sections = [
        SectionBlock(
            section_id="sec_1",
            course_id="COURSE_GEN",
            lesson_id="LESSON_GEN",
            name="章节概述",
            summary="概述本章主要内容。",
            page_range=[1],
            key_points=["数学模型的作用"],
            knowledge_points=["数学模型"],
            source_unit_ids=["unit_1"],
            section_type="intro",
        ),
        SectionBlock(
            section_id="sec_2",
            course_id="COURSE_GEN",
            lesson_id="LESSON_GEN",
            name="微分方程建模",
            summary="介绍建模步骤。",
            page_range=[2],
            key_points=["确定输入输出", "整理标准形式"],
            knowledge_points=["微分方程建模"],
            source_unit_ids=["unit_2"],
            section_type="content",
        ),
    ]
    structured_content = StructuredLessonContent(
        course_id="COURSE_GEN",
        lesson_id="LESSON_GEN",
        source_asset_ids=["asset_1"],
        lesson_summary="本章介绍控制系统数学模型与微分方程建模方法。",
        pages=pages,
        sections=sections,
        knowledge_points=["数学模型", "微分方程建模"],
        metadata={"source": "test"},
    )
    return GenerateInput(
        course_id="COURSE_GEN",
        lesson_id="LESSON_GEN",
        lesson_name="控制系统的数学模型",
        structured_content=structured_content,
        teacher_notes="请突出课程结构。",
        generate_instruction="优先压缩成适合展示的内容。",
    )


def test_generate_pipeline_uses_llm_sections_and_derives_outputs():
    generate_input = _build_generate_input()

    def fake_llm(*, stage, metadata, **_kwargs):
        assert stage == "generate_section"
        section = metadata["section"]
        section_pages = metadata["section_pages"]
        return {
            "section_id": section["section_id"],
            "title": section["name"],
            "summary": section["summary"],
            "cards": [
                {
                    "card_id": f"{section['section_id']}_card_1",
                    "card_type": "cover" if section["section_id"] == "sec_1" else "process",
                    "title": section_pages[0]["title"],
                    "bullets": section_pages[0]["key_points"],
                    "speaker_notes": section_pages[0]["summary"],
                    "visual_plan": [{"visual_type": "none", "source_unit_ids": [], "caption": ""}],
                    "source_section_ids": [section["section_id"]],
                    "source_page_ids": [section_pages[0]["page_id"]],
                    "source_unit_ids": section_pages[0]["source_unit_ids"],
                }
            ],
            "source_page_ids": [page["page_id"] for page in section_pages],
            "source_unit_ids": [unit_id for page in section_pages for unit_id in page["source_unit_ids"]],
        }

    result = run_generate_pipeline(generate_input=generate_input, llm_callable=fake_llm)

    assert result["used_fallback"] is False
    assert result["validation_errors"] == []
    assert result["presentation_outline"].lesson_title == "控制系统的数学模型"
    assert len(result["presentation_outline"].sections) == 2
    assert result["presentation_outline"].sections[0].cards[0].card_type == "cover"
    assert result["teacher_feedback_text"]
    assert len(result["lesson_script"].script_blocks) == 2
    assert len(result["ppt_outline"].slides) == 2


def test_generate_pipeline_falls_back_without_llm():
    generate_input = _build_generate_input()

    result = run_generate_pipeline(generate_input=generate_input, llm_callable=None)

    assert result["used_fallback"] is True
    assert len(result["presentation_outline"].sections) == 2
    assert result["presentation_outline"].metadata["fallback"] is True
    assert len(result["lesson_script"].script_blocks) == 2
    assert len(result["ppt_outline"].slides) == 2


def test_generate_pipeline_respects_max_sections_limit():
    generate_input = _build_generate_input()

    def fake_llm(*, stage, metadata, **_kwargs):
        assert stage == "generate_section"
        section = metadata["section"]
        page = metadata["section_pages"][0]
        return {
            "section_id": section["section_id"],
            "title": section["name"],
            "summary": section["summary"],
            "cards": [
                {
                    "card_id": f"{section['section_id']}_card_1",
                    "card_type": "concept",
                    "title": page["title"],
                    "bullets": page["key_points"],
                    "speaker_notes": page["summary"],
                    "visual_plan": [{"visual_type": "none", "source_unit_ids": [], "caption": ""}],
                    "source_section_ids": [section["section_id"]],
                    "source_page_ids": [page["page_id"]],
                    "source_unit_ids": page["source_unit_ids"],
                }
            ],
            "source_page_ids": [page["page_id"]],
            "source_unit_ids": page["source_unit_ids"],
        }

    result = run_generate_pipeline(
        generate_input=generate_input,
        llm_callable=fake_llm,
        max_sections=1,
    )

    assert result["used_fallback"] is False
    assert result["processed_section_count"] == 1
    assert result["total_input_sections"] == 2
    assert result["max_sections_applied"] == 1
    assert len(result["presentation_outline"].sections) == 1


def test_generate_pipeline_downcasts_extra_cover_cards():
    generate_input = _build_generate_input()

    def fake_llm(*, stage, metadata, **_kwargs):
        assert stage == "generate_section"
        section = metadata["section"]
        page = metadata["section_pages"][0]
        return {
            "section_id": section["section_id"],
            "title": section["name"],
            "summary": section["summary"],
            "cards": [
                {
                    "card_id": f"{section['section_id']}_card_1",
                    "card_type": "cover",
                    "title": page["title"],
                    "bullets": page["key_points"],
                    "speaker_notes": page["summary"],
                    "visual_plan": [{"visual_type": "none", "source_unit_ids": [], "caption": ""}],
                    "source_section_ids": [section["section_id"]],
                    "source_page_ids": [page["page_id"]],
                    "source_unit_ids": page["source_unit_ids"],
                }
            ],
            "source_page_ids": [page["page_id"]],
            "source_unit_ids": page["source_unit_ids"],
        }

    result = run_generate_pipeline(generate_input=generate_input, llm_callable=fake_llm)

    assert result["presentation_outline"].sections[0].cards[0].card_type == "cover"
    assert result["presentation_outline"].sections[1].cards[0].card_type != "cover"


def _build_small_section_generate_input() -> GenerateInput:
    pages = []
    sections = []
    for index in range(1, 4):
        page_id = f"page_{index}"
        section_id = f"sec_{index}"
        unit_id = f"unit_{index}"
        pages.append(
            PageBlock(
                page_id=page_id,
                course_id="COURSE_SMALL",
                lesson_id="LESSON_SMALL",
                section_id=section_id,
                page=index,
                title=f"Topic {index}",
                content=f"Content {index}",
                summary=f"Summary {index}",
                key_points=[f"Point {index}"],
                knowledge_points=[f"Knowledge {index}"],
                source_unit_ids=[unit_id],
                page_role="content",
                file_id="asset_small",
                file_type="pptx",
            )
        )
        sections.append(
            SectionBlock(
                section_id=section_id,
                course_id="COURSE_SMALL",
                lesson_id="LESSON_SMALL",
                name=f"Section {index}",
                summary=f"Summary {index}",
                page_range=[index],
                key_points=[f"Point {index}"],
                knowledge_points=[f"Knowledge {index}"],
                source_unit_ids=[unit_id],
                section_type="content",
            )
        )

    structured_content = StructuredLessonContent(
        course_id="COURSE_SMALL",
        lesson_id="LESSON_SMALL",
        source_asset_ids=["asset_small"],
        lesson_summary="Small section lesson summary",
        pages=pages,
        sections=sections,
        knowledge_points=[f"Knowledge {index}" for index in range(1, 4)],
        metadata={"source": "test"},
    )
    return GenerateInput(
        course_id="COURSE_SMALL",
        lesson_id="LESSON_SMALL",
        lesson_name="Small Section Lesson",
        structured_content=structured_content,
        teacher_notes="",
        generate_instruction="",
    )


def test_generate_pipeline_keeps_small_sections_separate_by_default():
    generate_input = _build_small_section_generate_input()

    def fake_llm(*, stage, metadata, **_kwargs):
        assert stage == "generate_section"
        section = metadata["section"]
        page = metadata["section_pages"][0]
        return {
            "section_id": section["section_id"],
            "title": section["name"],
            "summary": section["summary"],
            "cards": [
                {
                    "card_id": f"{section['section_id']}_card_1",
                    "card_type": "concept",
                    "title": page["title"],
                    "bullets": page["key_points"],
                    "speaker_notes": page["summary"],
                    "visual_plan": [{"visual_type": "none", "source_unit_ids": [], "caption": ""}],
                    "source_section_ids": [section["section_id"]],
                    "source_page_ids": [page["page_id"]],
                    "source_unit_ids": page["source_unit_ids"],
                }
            ],
            "source_page_ids": [page["page_id"]],
            "source_unit_ids": page["source_unit_ids"],
        }

    result = run_generate_pipeline(generate_input=generate_input, llm_callable=fake_llm)

    assert result["processed_section_count"] == 3
    assert [section.section_id for section in result["presentation_outline"].sections] == [
        "sec_1",
        "sec_2",
        "sec_3",
    ]


def test_generate_pipeline_does_not_batch_by_default_in_parallel_mode():
    generate_input = _build_small_section_generate_input()
    stages = []

    def fake_llm(*, stage, metadata, **_kwargs):
        stages.append(stage)
        assert stage == "generate_section"
        section = metadata["section"]
        page = metadata["section_pages"][0]
        return {
            "section_id": section["section_id"],
            "title": section["name"],
            "summary": section["summary"],
            "cards": [
                {
                    "card_id": f"{section['section_id']}_card_1",
                    "card_type": "concept",
                    "title": page["title"],
                    "bullets": page["key_points"],
                    "speaker_notes": page["summary"],
                    "visual_plan": [{"visual_type": "none", "source_unit_ids": [], "caption": ""}],
                    "source_section_ids": [section["section_id"]],
                    "source_page_ids": [page["page_id"]],
                    "source_unit_ids": page["source_unit_ids"],
                }
            ],
            "source_page_ids": [page["page_id"]],
            "source_unit_ids": page["source_unit_ids"],
        }

    result = run_generate_pipeline(
        generate_input=generate_input,
        llm_callable=fake_llm,
        max_workers=2,
    )

    assert result["used_fallback"] is False
    assert stages == ["generate_section", "generate_section", "generate_section"]


def test_build_section_payload_is_compact_but_keeps_teaching_fields():
    generate_input = _build_small_section_generate_input()
    section = generate_input.sections[0]
    section_pages = [generate_input.pages[0]]
    prompt_config = {
        "section_generation_prompt": {
            "user_template": "{section_payload}",
        }
    }

    payload = _build_section_payload(
        generate_input=generate_input,
        section=section,
        section_pages=section_pages,
        prompt_config=prompt_config,
    )

    assert '"section_id": "sec_1"' in payload
    assert '"title": "Topic 1"' in payload
    assert '"content": "Content 1"' in payload
    assert '"course_id"' not in payload
    assert '"lesson_id"' not in payload
    assert '"file_id"' not in payload
    assert '"file_type"' not in payload
