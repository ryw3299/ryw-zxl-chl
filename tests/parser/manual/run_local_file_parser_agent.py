import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src.agents.file_parser import build_file_parser_stages
from src.utils.file_loader import detect_file_type
from src.utils.logging_utils import resolve_runtime_output_path
from src.utils.path_utils import ensure_existing_file, parse_asset_input_lines

DEFAULT_ENV_PATH = REPO_ROOT / ".env"


def main() -> None:
    print("=== File Parser Agent Manual Runner ===")
    print("This script uses the real file_parser agent entry.")
    print("It loads the repo .env, runs the parser pipeline, then attempts LLM structuring.")
    print("If LLM structuring fails, the agent will fall back to baseline structured content.")
    print("")

    if not DEFAULT_ENV_PATH.exists():
        print("=== Missing .env ===")
        print(f"Expected env file: {DEFAULT_ENV_PATH}")
        print("Create .env in the repo root before running this script.")
        return

    raw_asset_specs = _prompt_asset_specs()
    course_id = _prompt_optional("Enter course_id (optional)")
    lesson_id = _prompt_optional("Enter lesson_id (optional, blank = auto generate)") or _default_lesson_id()
    parse_instruction = _prompt_optional("Enter parse_instruction (optional)")

    try:
        parsed_specs = parse_asset_input_lines(raw_asset_specs)
        if not parsed_specs:
            raise ValueError("At least one file path is required.")

        resolved_assets = []
        for index, (path_value, explicit_type) in enumerate(parsed_specs, start=1):
            resolved_path = ensure_existing_file(path_value)
            detected_type = detect_file_type(str(resolved_path), explicit_type)
            resolved_assets.append(
                {
                    "asset_id": f"manual_asset_{index}",
                    "file_path": str(resolved_path),
                    "file_type": detected_type,
                    "file_name": resolved_path.name,
                }
            )
    except Exception as exc:
        print("")
        print("=== Input Validation Failed ===")
        print(f"Reason: {exc}")
        print(_common_input_hints())
        return

    print("")
    print("=== Input Summary ===")
    print(f"Resolved asset count: {len(resolved_assets)}")
    for asset in resolved_assets:
        print(f"- {asset['file_type']}: {asset['file_path']}")
    print(f"Env file: {DEFAULT_ENV_PATH}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    requested_log_file = (
        REPO_ROOT / "tests" / "logs" / "parser" / "manual" / f"manual_parser_agent_{timestamp}.log"
    )
    requested_artifact_file = (
        REPO_ROOT / "tests" / "logs" / "parser" / "manual" / f"manual_parser_agent_{timestamp}.json"
    )

    request = {
        "course_id": _normalize_optional(course_id),
        "lesson_id": lesson_id,
        "assets": resolved_assets,
        "parse_instruction": _normalize_optional(parse_instruction),
    }

    try:
        stages = build_file_parser_stages(
            request,
            log_file=str(requested_log_file),
            env_path=str(DEFAULT_ENV_PATH),
        )
    except Exception as exc:
        print("")
        print("=== Parser Agent Failed ===")
        print(f"Reason: {exc}")
        print(_common_parser_hints(", ".join(sorted({asset["file_type"] for asset in resolved_assets}))))
        print(f"Expected log file: {requested_log_file}")
        return

    output = stages["output"].model_dump(mode="python")
    artifact_path = resolve_runtime_output_path(str(requested_artifact_file))
    if artifact_path is None:
        raise RuntimeError("Artifact path resolution failed.")

    stage_payload = {
        "parser_input": stages["request"].model_dump(mode="python"),
        "parsed_document": stages["parsed_document"].model_dump(mode="python"),
        "baseline_structured_content": stages["baseline_structured_content"].model_dump(mode="python"),
        "final_structured_content": stages["structured_content"].model_dump(mode="python"),
        "structuring_result": _to_jsonable(stages["structuring_result"]),
        "parser_output": output,
    }
    artifact_path.write_text(json.dumps(stage_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    structuring_meta = output.get("metadata", {})
    used_fallback = structuring_meta.get("structuring_used_fallback")

    _print_stage(
        title="Stage 1: ParserInput",
        description="Validated request payload after schema normalization.",
        payload=stage_payload["parser_input"],
    )
    _print_stage(
        title="Stage 2: ParsedDocument",
        description="Deterministic parser-layer result. This is the source-grounded input to the agent structuring step.",
        payload=stage_payload["parsed_document"],
    )
    _print_stage(
        title="Stage 3: Baseline StructuredLessonContent",
        description="Rule-based structured result produced before LLM structuring. This is also the fallback target.",
        payload=stage_payload["baseline_structured_content"],
    )
    _print_stage(
        title="Stage 4: Structuring Result Metadata",
        description="Shows whether the agent used single-pass or chunked structuring, and whether fallback was triggered.",
        payload=stage_payload["structuring_result"],
    )
    _print_stage(
        title="Stage 5: Final StructuredLessonContent",
        description="Final structured summary used by the agent. If fallback happened, this will match the baseline result.",
        payload=stage_payload["final_structured_content"],
    )
    _print_stage(
        title="Stage 6: ParserOutput",
        description="Final standard output returned by the parser agent.",
        payload=stage_payload["parser_output"],
    )

    print("")
    print("=== Agent Outcome Summary ===")
    print(f"structuring_enabled: {structuring_meta.get('structuring_enabled')}")
    print(f"structuring_strategy: {structuring_meta.get('structuring_strategy')}")
    print(f"structuring_chunk_count: {structuring_meta.get('structuring_chunk_count')}")
    print(f"structuring_used_fallback: {used_fallback}")
    print(f"structuring_validation_errors: {structuring_meta.get('structuring_validation_errors')}")
    if used_fallback:
        print(
            "Note: The agent fell back to baseline structured content. Check the log file for the exact LLM or validation error."
        )
    else:
        print("Note: The agent successfully used the LLM-structured result.")

    print("")
    print("=== Output Files ===")
    print(f"log_file: {structuring_meta.get('log_file')}")
    print(f"artifact_file: {artifact_path}")


def _prompt_optional(label: str) -> str:
    return input(f"{label}: ").strip()


def _default_lesson_id() -> str:
    return f"LESSON_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def _normalize_optional(value: str) -> str | None:
    normalized = value.strip()
    return normalized or None


def _prompt_asset_specs() -> list[str]:
    print("Enter one or more file paths.")
    print("Optional per-file format: path|type")
    print("Examples:")
    print(r'  "C:\Users\Lenovo\Desktop\demo.pptx"')
    print(r"  C:\Users\Lenovo\Desktop\notes.pdf|pdf")

    raw_lines: list[str] = []
    index = 1
    while True:
        line = input(f"file path #{index}: ").strip()
        if not line:
            if raw_lines:
                return raw_lines
            print("At least one file path is required.")
            continue
        raw_lines.append(line)
        if not _prompt_yes_no("Add another file? (y/N)", default=False):
            return raw_lines
        index += 1


def _prompt_yes_no(label: str, default: bool = False) -> bool:
    raw = input(f"{label}: ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes"}


def _print_stage(title: str, description: str, payload: Any) -> None:
    print("")
    print(f"=== {title} ===")
    print(description)
    print(json.dumps(_truncate_payload(payload), ensure_ascii=False, indent=2))


def _truncate_payload(payload: Any, max_string_length: int = 300) -> Any:
    if isinstance(payload, dict):
        return {
            key: _truncate_payload(value, max_string_length=max_string_length)
            for key, value in payload.items()
        }
    if isinstance(payload, list):
        return [_truncate_payload(item, max_string_length=max_string_length) for item in payload]
    if isinstance(payload, str) and len(payload) > max_string_length:
        return payload[: max_string_length - 3] + "..."
    return payload


def _to_jsonable(payload: Any) -> Any:
    if hasattr(payload, "model_dump"):
        return _to_jsonable(payload.model_dump(mode="python"))
    if isinstance(payload, dict):
        return {key: _to_jsonable(value) for key, value in payload.items()}
    if isinstance(payload, list):
        return [_to_jsonable(item) for item in payload]
    return payload


def _common_input_hints() -> str:
    return "\n".join(
        [
            "Common checks:",
            r"- Paste the real absolute path, for example: E:\your\file.pdf",
            "- Outer single quotes or double quotes are allowed.",
            "- For multiple files, enter one path per line.",
            "- Optional per-file override format: path|type",
            "- Make sure the file extension matches the real file type.",
            "- If the file is on Desktop or Downloads, confirm the path is the Windows local path, not a browser URL.",
        ]
    )


def _common_parser_hints(file_type: str) -> str:
    hints = [
        "Common parser checks:",
        "- The file may be corrupted or locked by another program.",
        "- The file extension may not match the actual file content.",
        "- The .env configuration may be incomplete or the API request may have failed.",
    ]

    if file_type == "pdf":
        hints.extend(
            [
                "- If this is a scanned PDF or image-only PDF, the current version cannot OCR it yet.",
                "- If the PDF is password-protected or encrypted, PyMuPDF will fail to open it.",
            ]
        )
    if file_type == "ppt":
        hints.append("- Legacy .ppt requires auto-conversion to .pptx before parsing.")
        hints.append("- Auto-conversion requires LibreOffice installed on this machine.")

    return "\n".join(hints)


if __name__ == "__main__":
    main()
