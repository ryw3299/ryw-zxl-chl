import json
from pathlib import Path

from src.agents.file_parser import run_file_parser
from src.schemas import ParserOutput
from src.utils.logging_utils import resolve_runtime_output_path

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_FILE = REPO_ROOT / "tests" / "parser" / "fixtures" / "sample_lesson.txt"
LOG_DIR = REPO_ROOT / "tests" / "logs" / "parser" / "integration"
LOG_FILE = LOG_DIR / "user_input_to_parser_output.log"
ARTIFACT_FILE = LOG_DIR / "user_input_to_parser_output.json"


def test_user_input_to_parser_output_chain():
    request = {
        "course_id": "COURSE_DEMO",
        "lesson_id": "LESSON_DEMO",
        "assets": [
            {
                "asset_id": "asset_txt_1",
                "file_path": str(FIXTURE_FILE),
                "file_type": "txt",
                "file_name": FIXTURE_FILE.name,
                "mime_type": "text/plain",
            }
        ],
        "parse_instruction": "保留定义和核心概念，便于后续生成智课讲稿。",
    }

    output = run_file_parser(request, log_file=str(LOG_FILE))
    artifact_path = resolve_runtime_output_path(str(ARTIFACT_FILE))
    assert artifact_path is not None
    artifact_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    result = ParserOutput.model_validate(output)
    runtime_log_path = Path(result.metadata["log_file"])

    assert result.status == "success"
    assert result.parsed_document is not None
    assert result.structured_content is not None
    assert result.total_units == 2
    assert result.total_pages == 2
    assert len(result.source_assets) == 1
    assert len(result.parsed_document.units) == 2
    assert len(result.structured_content.pages) == 2
    assert len(result.structured_content.sections) == 2
    assert result.structured_content.parse_instruction == request["parse_instruction"]
    assert runtime_log_path.exists()
    assert artifact_path.exists()
