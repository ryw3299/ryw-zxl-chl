import json
from pathlib import Path

import src.main as cli_main


def test_main_teacher_workflow_command_writes_result(monkeypatch):
    artifact_dir = Path(__file__).resolve().parent / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    request_file = artifact_dir / "teacher_workflow_request.json"
    output_file = artifact_dir / "teacher_workflow_result.json"

    request_payload = {
        "course_id": "COURSE_CLI",
        "lesson_id": "LESSON_CLI",
        "lesson_name": "CLI Lesson",
        "assets": [
            {
                "asset_id": "asset_1",
                "file_path": r"E:\demo\lesson.pdf",
                "file_type": "pdf",
                "file_name": "lesson.pdf",
            }
        ],
        "parse_instruction": "Focus on key concepts.",
        "teacher_notes": "Speak clearly.",
        "generate_instruction": "Keep slides concise.",
    }
    request_file.write_text(json.dumps(request_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    captured = {}

    def fake_run_teacher_workflow(teacher_input, **kwargs):
        captured["teacher_input"] = teacher_input
        captured["kwargs"] = kwargs
        return {
            "status": "success",
            "message": "teacher workflow finished",
            "lesson_id": teacher_input["lesson_id"],
            "artifact_file": kwargs.get("artifact_file"),
            "rendered_ppt_file": kwargs.get("rendered_ppt_file"),
        }

    monkeypatch.setattr(cli_main, "run_teacher_workflow", fake_run_teacher_workflow)

    exit_code = cli_main.main(
        [
            "teacher-workflow",
            "--request-file",
            str(request_file),
            "--output-file",
            str(output_file),
            "--artifact-file",
            str(artifact_dir / "artifact.json"),
            "--rendered-ppt-file",
            str(artifact_dir / "rendered.pptx"),
            "--parser-max-workers",
            "3",
            "--generate-max-workers",
            "2",
            "--skip-render-ppt",
        ]
    )

    assert exit_code == 0
    assert captured["teacher_input"]["lesson_id"] == "LESSON_CLI"
    assert captured["kwargs"]["parser_max_workers"] == 3
    assert captured["kwargs"]["generate_max_workers"] == 2
    assert captured["kwargs"]["render_ppt"] is False
    assert output_file.exists()

    result_payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert result_payload["status"] == "success"
    assert result_payload["lesson_id"] == "LESSON_CLI"
