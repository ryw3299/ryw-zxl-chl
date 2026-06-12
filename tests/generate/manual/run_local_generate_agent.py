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

from src.utils.file_loader import detect_file_type
from src.utils.logging_utils import resolve_runtime_output_path
from src.utils.path_utils import ensure_existing_file, parse_asset_input_lines
from src.workflows import build_teacher_workflow_stages

DEFAULT_ENV_PATH = REPO_ROOT / ".env"


def main() -> None:
    print("=== Generate Agent Manual Runner ===")
    print("This runner executes: local files -> parser -> generate.")
    print("It loads .env, builds StructuredLessonContent, then generates teacher-facing assets.")
    print("Quality-first defaults are enabled for generate: auto workers, no default batching.")
    print("")

    if not DEFAULT_ENV_PATH.exists():
        print("=== Missing .env ===")
        print(f"Expected env file: {DEFAULT_ENV_PATH}")
        print("Create .env in the repo root before running this script.")
        return

    raw_asset_specs = _prompt_asset_specs()
    course_id = _prompt_optional("Enter course_id (optional)")
    lesson_id = _prompt_optional("Enter lesson_id (optional, blank = auto generate)") or _default_lesson_id()
    lesson_name = _prompt_optional("Enter lesson_name (optional, blank = infer from first file)")
    parse_instruction = _prompt_optional("Enter parse_instruction (optional)")
    teacher_notes = _prompt_optional("Enter teacher_notes (optional)")
    generate_instruction = _prompt_optional("Enter generate_instruction (optional)")
    preview_mode = _prompt_yes_no("Enable generate preview mode? (y/N)", default=False)
    max_sections = (
        _prompt_optional_int("Enter max_sections for preview (blank = 6)", default=6)
        if preview_mode
        else None
    )
    parser_max_workers = _prompt_optional_int("Enter parser max_workers (blank = 3, 1 = serial)", default=3)
    parser_batch_size = _prompt_optional_positive_int(
        "Enter parser batch_size (blank = pipeline default, 1 = no batching)"
    )
    generate_max_workers = _prompt_optional_positive_int(
        "Enter generate max_workers (blank = auto, 1 = serial)"
    )
    generate_batch_size = _prompt_optional_positive_int(
        "Enter generate batch_size (blank = default 1, 1 = no batching)"
    )
    render_ppt = _prompt_yes_no("Render .pptx from generated outline? (Y/n)", default=True)

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

    inferred_lesson_name = lesson_name.strip() or Path(resolved_assets[0]["file_name"]).stem

    print("")
    print("=== Input Summary ===")
    print(f"Resolved asset count: {len(resolved_assets)}")
    for asset in resolved_assets:
        print(f"- {asset['file_type']}: {asset['file_path']}")
    print(f"lesson_name: {inferred_lesson_name}")
    print(f"preview_mode: {preview_mode}")
    if max_sections is not None:
        print(f"max_sections: {max_sections}")
    print(
        "parser scheduling: "
        f"max_workers={parser_max_workers}, batch_size={_display_optional_int(parser_batch_size, fallback='pipeline default')}"
    )
    print(
        "generate scheduling request: "
        f"max_workers={_display_optional_int(generate_max_workers, fallback='auto')}, "
        f"batch_size={_display_optional_int(generate_batch_size, fallback='default 1')}"
    )
    if parser_max_workers > 5:
        print("[WARNING] parser max_workers > 5 may cause API rate limits. Consider using 3-5.")
    if parser_batch_size is not None and parser_batch_size > 5:
        print("[WARNING] parser batch_size > 5 may increase chunk failure blast radius.")
    if generate_max_workers is not None and generate_max_workers > 3:
        print("[WARNING] generate max_workers > 3 may reduce stability on large lessons.")
    if generate_batch_size is not None and generate_batch_size > 1:
        print("[WARNING] generate batch_size > 1 may reduce quality/stability. Recommended: blank or 1.")
    print(f"Env file: {DEFAULT_ENV_PATH}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    requested_parser_log_file = (
        REPO_ROOT / "tests" / "logs" / "generate" / "manual" / f"manual_generate_parser_{timestamp}.log"
    )
    requested_generate_log_file = (
        REPO_ROOT / "tests" / "logs" / "generate" / "manual" / f"manual_generate_agent_{timestamp}.log"
    )
    requested_artifact_file = (
        REPO_ROOT / "tests" / "logs" / "generate" / "manual" / f"manual_generate_agent_{timestamp}.json"
    )
    requested_ppt_file = (
        REPO_ROOT / "tests" / "logs" / "generate" / "manual" / f"manual_generate_agent_{timestamp}.pptx"
    )

    teacher_request = {
        "course_id": _normalize_optional(course_id),
        "lesson_id": lesson_id,
        "lesson_name": inferred_lesson_name,
        "assets": resolved_assets,
        "parse_instruction": _normalize_optional(parse_instruction),
        "teacher_notes": _normalize_optional(teacher_notes) or "",
        "generate_instruction": _normalize_optional(generate_instruction) or "",
    }

    try:
        workflow_stages = build_teacher_workflow_stages(
            teacher_request,
            parser_log_file=str(requested_parser_log_file),
            generate_log_file=str(requested_generate_log_file),
            artifact_file=str(requested_artifact_file),
            rendered_ppt_file=str(requested_ppt_file),
            env_path=str(DEFAULT_ENV_PATH),
            parser_max_workers=parser_max_workers,
            parser_batch_size=parser_batch_size,
            generate_max_sections=max_sections,
            generate_max_workers=generate_max_workers,
            generate_batch_size=generate_batch_size,
            render_ppt=render_ppt,
        )
    except Exception as exc:
        print("")
        print("=== Teacher Workflow Failed ===")
        print(f"Reason: {exc}")
        print(_common_parser_hints(", ".join(sorted({asset["file_type"] for asset in resolved_assets}))))
        print(f"Expected parser log file: {requested_parser_log_file}")
        print(f"Expected generate log file: {requested_generate_log_file}")
        return

    parser_stages = workflow_stages["parser_stages"]
    generate_stages = workflow_stages["generate_stages"]
    parser_output = parser_stages["output"].model_dump(mode="python")
    generate_output = generate_stages["output"].model_dump(mode="python")
    artifact_path = resolve_runtime_output_path(str(requested_artifact_file))
    if artifact_path is None:
        raise RuntimeError("Artifact path resolution failed.")
    rendered_ppt_path = workflow_stages["rendered_ppt_path"]

    if workflow_stages["output"]["metadata"].get("render_error"):
        print("")
        print("=== PPT Render Warning ===")
        print(f"Reason: {workflow_stages['output']['metadata']['render_error']}")
        print("Generate artifacts were still produced, but .pptx rendering failed.")

    artifact_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact_payload["runner_config"] = {
        "preview_mode": preview_mode,
        "max_sections": max_sections,
        "parser_max_workers": parser_max_workers,
        "parser_batch_size": parser_batch_size,
        "generate_max_workers": generate_max_workers,
        "generate_batch_size": generate_batch_size,
        "render_ppt": render_ppt,
    }
    artifact_path.write_text(json.dumps(artifact_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    parser_meta = parser_output.get("metadata", {})
    generate_meta = generate_output.get("metadata", {})
    presentation_outline = generate_output.get("presentation_outline", {}) or {}
    lesson_script = generate_output.get("lesson_script", {}) or {}
    ppt_outline = generate_output.get("ppt_outline", {}) or {}
    generation_section_errors = generate_meta.get("generation_section_errors", []) or []
    fallback_section_errors = [item for item in generation_section_errors if item.get("used_fallback")]

    print("")
    print("=== Parser Summary ===")
    print(f"total_units: {parser_output.get('total_units')}")
    print(f"total_pages: {parser_output.get('total_pages')}")
    print(f"structuring_enabled: {parser_meta.get('structuring_enabled')}")
    print(f"structuring_used_fallback: {parser_meta.get('structuring_used_fallback')}")

    print("")
    print("=== Teacher Feedback ===")
    print((generate_output.get("teacher_feedback_text") or "").strip() or "(empty)")

    print("")
    print("=== Presentation Outline Preview ===")
    print(f"lesson_title: {presentation_outline.get('lesson_title')}")
    print(f"section_count: {len(presentation_outline.get('sections', []) or [])}")
    print(f"knowledge_point_count: {len(presentation_outline.get('knowledge_points', []) or [])}")
    for index, section in enumerate((presentation_outline.get("sections", []) or [])[:6], start=1):
        cards = section.get("cards", []) or []
        print(f"{index}. {section.get('title', '')} ({len(cards)} cards)")
        for card_index, card in enumerate(cards[:3], start=1):
            print(f"   - {card_index}. [{card.get('card_type', '')}] {card.get('title', '')}")
        if len(cards) > 3:
            print(f"   - ... ({len(cards)} cards total)")

    print("")
    print("=== Lesson Script Preview ===")
    script_blocks = lesson_script.get("script_blocks", []) or []
    print(f"script_block_count: {len(script_blocks)}")
    for index, block in enumerate(script_blocks[:5], start=1):
        print(f"{index}. [{block.get('block_type', '')}] {block.get('title', '')}")

    print("")
    print("=== PPT Outline Preview ===")
    slides = ppt_outline.get("slides", []) or []
    print(f"slide_count: {len(slides)}")
    for index, slide in enumerate(slides[:6], start=1):
        print(f"{index}. [{slide.get('slide_type', '')}] {slide.get('title', '')}")

    print("")
    print("=== Generate Outcome Summary ===")
    print(f"generation_enabled: {generate_meta.get('generation_enabled')}")
    print(f"generation_used_fallback: {generate_meta.get('generation_used_fallback')}")
    print(f"generation_processed_sections: {generate_meta.get('generation_processed_sections')}")
    print(f"generation_total_input_sections: {generate_meta.get('generation_total_input_sections')}")
    print(f"generation_max_sections: {generate_meta.get('generation_max_sections')}")
    print(f"generation_max_workers_resolved: {generate_meta.get('generation_max_workers')}")
    print(f"generation_batch_size_resolved: {generate_meta.get('generation_batch_size')}")
    print(f"generation_validation_errors: {generate_meta.get('generation_validation_errors')}")
    print(f"generation_fallback_section_count: {len(fallback_section_errors)}")
    for item in fallback_section_errors[:5]:
        print(f"- fallback section: {item.get('section_id')} | errors={item.get('errors')}")

    print("")
    print("=== Output Files ===")
    print(f"parser_log_file: {parser_meta.get('log_file')}")
    print(f"generate_log_file: {generate_meta.get('log_file')}")
    print(f"artifact_file: {artifact_path}")
    print(f"rendered_ppt_file: {rendered_ppt_path if rendered_ppt_path else '(not rendered)'}")


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


def _prompt_optional_int(label: str, default: int) -> int:
    raw = input(f"{label}: ").strip()
    if not raw:
        return default
    value = int(raw)
    if value <= 0:
        raise ValueError("value must be greater than 0.")
    return value


def _prompt_optional_positive_int(label: str) -> int | None:
    raw = input(f"{label}: ").strip()
    if not raw:
        return None
    value = int(raw)
    if value <= 0:
        raise ValueError("value must be greater than 0.")
    return value


def _display_optional_int(value: int | None, fallback: str) -> str:
    return str(value) if value is not None else fallback


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
