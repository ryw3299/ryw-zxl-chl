from src.agents.generate import build_generate_stages
from src.schemas import PageBlock, SectionBlock, StructuredLessonContent


def _build_request() -> dict:
    pages = [
        PageBlock(
            page_id="page_1",
            course_id="COURSE_AGENT_GEN",
            lesson_id="LESSON_AGENT_GEN",
            section_id="sec_1",
            page=1,
            title="根轨迹法概述",
            content="介绍根轨迹法的主要作用。",
            summary="介绍根轨迹法的用途。",
            key_points=["根轨迹的作用", "课程结构"],
            knowledge_points=["根轨迹法"],
            source_unit_ids=["unit_1"],
            page_role="cover",
            file_id="asset_1",
            file_type="pptx",
        )
    ]
    sections = [
        SectionBlock(
            section_id="sec_1",
            course_id="COURSE_AGENT_GEN",
            lesson_id="LESSON_AGENT_GEN",
            name="章节概述",
            summary="介绍根轨迹法内容。",
            page_range=[1],
            key_points=["根轨迹的作用"],
            knowledge_points=["根轨迹法"],
            source_unit_ids=["unit_1"],
            section_type="intro",
        )
    ]
    structured_content = StructuredLessonContent(
        course_id="COURSE_AGENT_GEN",
        lesson_id="LESSON_AGENT_GEN",
        source_asset_ids=["asset_1"],
        lesson_summary="本节介绍根轨迹法的基本内容。",
        pages=pages,
        sections=sections,
        knowledge_points=["根轨迹法"],
        metadata={"source": "test"},
    )
    return {
        "course_id": "COURSE_AGENT_GEN",
        "lesson_id": "LESSON_AGENT_GEN",
        "lesson_name": "根轨迹法",
        "structured_content": structured_content.model_dump(mode="python"),
        "teacher_notes": "适合课堂展示。",
        "generate_instruction": "突出定义和方法步骤。",
    }


def test_generate_agent_uses_pipeline_result_when_llm_is_available():
    request = _build_request()

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
                    "card_id": "card_1",
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

    stages = build_generate_stages(request, llm_callable=fake_llm)
    output = stages["output"]

    assert output.presentation_outline.lesson_title == "根轨迹法"
    assert output.teacher_feedback_text
    assert len(output.lesson_script.script_blocks) == 1
    assert len(output.ppt_outline.slides) == 1
    assert output.metadata["generation_enabled"] is True
    assert output.metadata["generation_used_fallback"] is False


def test_generate_agent_uses_safe_parallelism_by_default_for_multiple_sections():
    request = _build_request()
    pages = request["structured_content"]["pages"]
    sections = request["structured_content"]["sections"]

    request["structured_content"]["pages"] = [{**pages[0]} for _ in range(3)]
    request["structured_content"]["sections"] = [
        {
            **sections[0],
            "section_id": f"sec_{index}",
            "name": f"section_{index}",
            "page_range": [index],
            "source_unit_ids": [f"unit_{index}"],
        }
        for index in range(1, 4)
    ]
    for index, page in enumerate(request["structured_content"]["pages"], start=1):
        page["page_id"] = f"page_{index}"
        page["section_id"] = f"sec_{index}"
        page["page"] = index
        page["source_unit_ids"] = [f"unit_{index}"]
        page["title"] = f"title_{index}"
        page["summary"] = f"summary_{index}"
        page["key_points"] = [f"point_{index}"]

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

    stages = build_generate_stages(request, llm_callable=fake_llm)
    output = stages["output"]

    assert output.metadata["generation_max_workers"] == 3
    assert output.metadata["generation_batch_size"] == 1
