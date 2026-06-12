import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.agents.file_parser import run_file_parser
from src.schemas import ParserOutput
from src.utils.logging_utils import resolve_runtime_output_path


def main() -> None:
    fixture_file = REPO_ROOT / "tests" / "parser" / "fixtures" / "sample_lesson.txt"
    requested_log_file = (
        REPO_ROOT / "tests" / "logs" / "parser" / "integration" / "user_input_to_parser_output.log"
    )
    requested_artifact_file = (
        REPO_ROOT / "tests" / "logs" / "parser" / "integration" / "user_input_to_parser_output.json"
    )

    request = {
        "course_id": "COURSE_DEMO",
        "lesson_id": "LESSON_DEMO",
        "assets": [
            {
                "asset_id": "asset_txt_1",
                "file_path": str(fixture_file),
                "file_type": "txt",
                "file_name": fixture_file.name,
                "mime_type": "text/plain",
            }
        ],
        "parse_instruction": "保留定义和核心概念，便于后续生成智课讲稿。",
    }

    output = run_file_parser(request, log_file=str(requested_log_file))
    artifact_path = resolve_runtime_output_path(str(requested_artifact_file))
    if artifact_path is None:
        raise RuntimeError("Artifact path resolution failed.")

    artifact_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    result = ParserOutput.model_validate(output)
    print("status:", result.status)
    print("lesson_id:", result.lesson_id)
    print("total_units:", result.total_units)
    print("total_pages:", result.total_pages)
    print("log_file:", result.metadata.get("log_file"))
    print("artifact_file:", artifact_path)


if __name__ == "__main__":
    main()
