import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.agents.file_parser import run_file_parser
from src.schemas import ParserOutput
from src.utils.logging_utils import resolve_runtime_output_path
from tests.parser.helpers import build_sample_parser_assets


def main() -> None:
    generated_fixture_dir = REPO_ROOT / "tests" / "parser" / "fixtures" / "generated"
    requested_log_file = (
        REPO_ROOT / "tests" / "logs" / "parser" / "integration" / "supported_asset_parsers.log"
    )
    requested_artifact_file = (
        REPO_ROOT / "tests" / "logs" / "parser" / "integration" / "supported_asset_parsers.json"
    )
    sample_assets = build_sample_parser_assets(generated_fixture_dir)

    request = {
        "course_id": "COURSE_MULTI",
        "lesson_id": "LESSON_MULTI",
        "assets": [
            _build_asset_payload("asset_txt_1", sample_assets["txt"], "txt", "text/plain"),
            _build_asset_payload("asset_pdf_1", sample_assets["pdf"], "pdf", "application/pdf"),
            _build_asset_payload(
                "asset_pptx_1",
                sample_assets["pptx"],
                "pptx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ),
            _build_asset_payload(
                "asset_docx_1",
                sample_assets["docx"],
                "docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
        ],
        "parse_instruction": "按适合生成智课和讲义的方式整理内容，保留标题映射。",
    }

    output = run_file_parser(request, log_file=str(requested_log_file))
    artifact_path = resolve_runtime_output_path(str(requested_artifact_file))
    if artifact_path is None:
        raise RuntimeError("Artifact path resolution failed.")

    artifact_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    result = ParserOutput.model_validate(output)
    unit_type_counts = Counter(unit.unit_type for unit in result.parsed_document.units)

    print("status:", result.status)
    print("lesson_id:", result.lesson_id)
    print("total_units:", result.total_units)
    print("total_pages:", result.total_pages)
    print("unit_type_counts:", dict(unit_type_counts))
    print("log_file:", result.metadata.get("log_file"))
    print("artifact_file:", artifact_path)


def _build_asset_payload(asset_id: str, path: Path, file_type: str, mime_type: str) -> dict:
    return {
        "asset_id": asset_id,
        "file_path": str(path),
        "file_type": file_type,
        "file_name": path.name,
        "mime_type": mime_type,
    }


if __name__ == "__main__":
    main()
