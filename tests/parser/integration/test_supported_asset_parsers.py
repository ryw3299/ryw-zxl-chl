import json
from collections import Counter
from pathlib import Path

from src.agents.file_parser import run_file_parser
from src.schemas import ParserOutput
from src.utils.logging_utils import resolve_runtime_output_path
from tests.parser.helpers import build_sample_parser_assets

REPO_ROOT = Path(__file__).resolve().parents[3]
GENERATED_FIXTURE_DIR = REPO_ROOT / "tests" / "parser" / "fixtures" / "generated"
LOG_DIR = REPO_ROOT / "tests" / "logs" / "parser" / "integration"
LOG_FILE = LOG_DIR / "supported_asset_parsers.log"
ARTIFACT_FILE = LOG_DIR / "supported_asset_parsers.json"


def test_supported_asset_parsers_chain():
    sample_assets = build_sample_parser_assets(GENERATED_FIXTURE_DIR)

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

    output = run_file_parser(request, log_file=str(LOG_FILE))
    artifact_path = resolve_runtime_output_path(str(ARTIFACT_FILE))
    assert artifact_path is not None
    artifact_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    result = ParserOutput.model_validate(output)
    runtime_log_path = Path(result.metadata["log_file"])
    unit_type_counts = Counter(unit.unit_type for unit in result.parsed_document.units)

    assert result.status == "success"
    assert result.parsed_document is not None
    assert result.structured_content is not None
    assert len(result.source_assets) == 4
    assert result.total_units == 8
    assert result.total_pages == 8
    assert len(result.parsed_document.units) == 8
    assert unit_type_counts == {
        "chunk": 2,
        "page": 2,
        "slide": 2,
        "section": 2,
    }
    assert len(result.structured_content.pages) == 8
    assert len(result.structured_content.sections) == 8
    assert result.structured_content.parse_instruction == request["parse_instruction"]
    assert runtime_log_path.exists()
    assert artifact_path.exists()


def _build_asset_payload(asset_id: str, path: Path, file_type: str, mime_type: str) -> dict:
    return {
        "asset_id": asset_id,
        "file_path": str(path),
        "file_type": file_type,
        "file_name": path.name,
        "mime_type": mime_type,
    }
