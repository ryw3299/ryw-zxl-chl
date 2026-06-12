from pathlib import Path

from src.agents.file_parser import build_file_parser_stages

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_FILE = REPO_ROOT / "tests" / "parser" / "fixtures" / "sample_lesson.txt"


def test_file_parser_agent_uses_structuring_result_when_llm_is_available():
    request = {
        "course_id": "COURSE_AGENT",
        "lesson_id": "LESSON_AGENT",
        "assets": [
            {
                "asset_id": "asset_txt_1",
                "file_path": str(FIXTURE_FILE),
                "file_type": "txt",
                "file_name": FIXTURE_FILE.name,
                "mime_type": "text/plain",
            }
        ],
        "parse_instruction": "Focus on definitions and examples.",
    }

    def fake_llm(*, stage, metadata, **_kwargs):
        if stage != "single_pass":
            raise AssertionError(f"Unexpected stage: {stage}")

        units = metadata["parsed_document"]["units"]
        return {
            "lesson_summary": "Structured by LLM",
            "pages": [
                {
                    "page": index,
                    "title": unit["title"] or f"Unit {index}",
                    "summary": f"Structured summary for {unit['title'] or unit['unit_id']}",
                    "key_points": [unit["title"]] if unit["title"] else [],
                    "knowledge_points": [unit["title"]] if unit["title"] else [],
                    "source_unit_ids": [unit["unit_id"]],
                    "page_role": "content",
                    "section_id": f"draft_sec_{index}",
                }
                for index, unit in enumerate(units, start=1)
            ],
            "sections": [
                {
                    "section_id": f"draft_sec_{index}",
                    "name": unit["title"] or f"Section {index}",
                    "summary": f"Section summary for {unit['title'] or unit['unit_id']}",
                    "page_range": [index],
                    "key_points": [unit["title"]] if unit["title"] else [],
                    "knowledge_points": [unit["title"]] if unit["title"] else [],
                    "source_unit_ids": [unit["unit_id"]],
                    "section_type": "content",
                }
                for index, unit in enumerate(units, start=1)
            ],
            "knowledge_points": [unit["title"] for unit in units if unit["title"]],
        }

    stages = build_file_parser_stages(request, llm_callable=fake_llm)
    output = stages["output"]

    assert output.structured_content is not None
    assert output.structured_content.lesson_summary == "Structured by LLM"
    assert output.pages == output.structured_content.pages
    assert output.sections == output.structured_content.sections
    assert output.metadata["structuring_enabled"] is True
    assert output.metadata["structuring_used_fallback"] is False
    assert output.metadata["structuring_strategy"] == "single_pass"
    assert stages["baseline_structured_content"].lesson_summary != "Structured by LLM"
