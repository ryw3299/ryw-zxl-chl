from pathlib import Path

from src.workflows import build_teacher_workflow_stages

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_FILE = REPO_ROOT / "tests" / "parser" / "fixtures" / "sample_lesson.txt"


def test_teacher_workflow_runs_end_to_end_and_writes_outputs():
    request = {
        "course_id": "COURSE_WORKFLOW",
        "lesson_id": "LESSON_WORKFLOW",
        "lesson_name": "Workflow Lesson",
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
        "teacher_notes": "Use this for classroom delivery.",
        "generate_instruction": "Emphasize structure and key concepts.",
    }

    def fake_parser_llm(*, stage, metadata, **_kwargs):
        if stage != "single_pass":
            raise AssertionError(f"Unexpected parser stage: {stage}")

        units = metadata["parsed_document"]["units"]
        return {
            "lesson_summary": "Structured by parser LLM",
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

    def fake_generate_llm(*, stage, metadata, **_kwargs):
        if stage != "generate_section":
            raise AssertionError(f"Unexpected generate stage: {stage}")

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
                    "bullets": page["key_points"] or [page["summary"]],
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

    artifact_dir = Path(__file__).resolve().parent / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_file = artifact_dir / "teacher_workflow_artifact.json"
    ppt_file = artifact_dir / "teacher_workflow_rendered.pptx"

    stages = build_teacher_workflow_stages(
        request,
        artifact_file=str(artifact_file),
        rendered_ppt_file=str(ppt_file),
        parser_llm_callable=fake_parser_llm,
        generate_llm_callable=fake_generate_llm,
        render_ppt=True,
    )

    output = stages["output"]

    assert output["status"] == "success"
    assert output["lesson_name"] == "Workflow Lesson"
    assert output["parser_output"]["metadata"]["structuring_enabled"] is True
    assert output["generate_output"]["metadata"]["generation_enabled"] is True
    assert output["artifact_file"] == str(stages["artifact_path"])
    assert output["rendered_ppt_file"] == str(stages["rendered_ppt_path"])
    assert stages["artifact_path"].exists()
    assert stages["rendered_ppt_path"].exists()
