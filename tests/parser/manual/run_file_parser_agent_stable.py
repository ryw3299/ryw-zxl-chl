import json
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from src.agents.file_parser import run_file_parser
from src.utils.file_loader import detect_file_type
from src.utils.logging_utils import resolve_runtime_output_path
from src.utils.path_utils import ensure_existing_file, parse_asset_input_lines

DEFAULT_ENV_PATH = REPO_ROOT / ".env"


def main() -> None:
    print("=== File Parser Agent Stable Runner ===")
    print("This runner is for stable end-to-end execution only.")
    print("It prints a compact summary and saves the final parser output JSON.")
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
        REPO_ROOT / "tests" / "logs" / "parser" / "manual" / f"stable_parser_agent_{timestamp}.log"
    )
    requested_artifact_file = (
        REPO_ROOT / "tests" / "logs" / "parser" / "manual" / f"stable_parser_agent_{timestamp}.json"
    )

    request = {
        "course_id": _normalize_optional(course_id),
        "lesson_id": lesson_id,
        "assets": resolved_assets,
        "parse_instruction": _normalize_optional(parse_instruction),
    }

    try:
        output = run_file_parser(
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

    artifact_path = resolve_runtime_output_path(str(requested_artifact_file))
    if artifact_path is None:
        raise RuntimeError("Artifact path resolution failed.")
    artifact_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    metadata = output.get("metadata", {})
    structured_content = output.get("structured_content", {}) or {}
    sections = structured_content.get("sections", []) or []
    knowledge_points = structured_content.get("knowledge_points", []) or []

    print("")
    print("=== Stable Result Summary ===")
    print(f"status: {output.get('status')}")
    print(f"lesson_id: {output.get('lesson_id')}")
    print(f"total_units: {output.get('total_units')}")
    print(f"total_pages: {output.get('total_pages')}")
    print(f"structuring_enabled: {metadata.get('structuring_enabled')}")
    print(f"structuring_strategy: {metadata.get('structuring_strategy')}")
    print(f"structuring_used_fallback: {metadata.get('structuring_used_fallback')}")
    print(f"structuring_chunk_count: {metadata.get('structuring_chunk_count')}")

    print("")
    print("=== Lesson Summary ===")
    print((structured_content.get("lesson_summary") or "").strip() or "(empty)")

    print("")
    print("=== Section Preview ===")
    for index, section in enumerate(sections[:8], start=1):
        print(f"{index}. {section.get('name', '')}")
    if len(sections) > 8:
        print(f"... ({len(sections)} sections total)")

    print("")
    print("=== Knowledge Point Preview ===")
    for index, point in enumerate(knowledge_points[:12], start=1):
        print(f"{index}. {point}")
    if len(knowledge_points) > 12:
        print(f"... ({len(knowledge_points)} knowledge points total)")

    print("")
    print("=== Output Files ===")
    print(f"log_file: {metadata.get('log_file')}")
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


def _common_input_hints() -> str:
    return "\n".join(
        [
            "Common checks:",
            r"- Paste the real absolute path, for example: E:\your\file.pdf",
            "- Outer single quotes or double quotes are allowed.",
            "- For multiple files, enter one path per line.",
            "- Optional per-file override format: path|type",
            "- Make sure the file extension matches the real file type.",
        ]
    )


def _common_parser_hints(file_type: str) -> str:
    hints = [
        "Common parser checks:",
        "- The file may be corrupted or locked by another program.",
        "- The file extension may not match the actual file content.",
        "- The .env configuration may be incomplete or the API request may have failed.",
    ]

    if "pdf" in file_type:
        hints.extend(
            [
                "- If this is a scanned PDF or image-only PDF, the current version cannot OCR it yet.",
                "- If the PDF is password-protected or encrypted, PyMuPDF will fail to open it.",
            ]
        )
    if "ppt" in file_type:
        hints.append("- Legacy .ppt requires LibreOffice for auto-conversion to .pptx.")

    return "\n".join(hints)


if __name__ == "__main__":
    main()
