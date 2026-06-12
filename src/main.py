import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Optional

from src.workflows import run_teacher_workflow


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_argument_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "teacher-workflow":
        return _run_teacher_workflow_command(args)

    parser.print_help()
    return 1


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ChaoXingAgent command-line entrypoint")
    subparsers = parser.add_subparsers(dest="command")

    teacher_parser = subparsers.add_parser(
        "teacher-workflow",
        help="Run the teacher workflow from a JSON request file.",
    )
    teacher_parser.add_argument(
        "--request-file", required=True, help="Path to the teacher workflow request JSON file."
    )
    teacher_parser.add_argument(
        "--output-file", required=True, help="Path to write the workflow result JSON."
    )
    teacher_parser.add_argument("--env-path", help="Optional .env file path for LLM configuration.")
    teacher_parser.add_argument("--parser-log-file", help="Optional parser log file path.")
    teacher_parser.add_argument("--generate-log-file", help="Optional generate log file path.")
    teacher_parser.add_argument("--artifact-file", help="Optional workflow artifact JSON file path.")
    teacher_parser.add_argument("--rendered-ppt-file", help="Optional rendered PPTX output path.")
    teacher_parser.add_argument(
        "--parser-max-workers", type=int, help="Optional parser max_workers override."
    )
    teacher_parser.add_argument("--parser-batch-size", type=int, help="Optional parser batch_size override.")
    teacher_parser.add_argument(
        "--generate-max-sections", type=int, help="Optional preview max_sections limit."
    )
    teacher_parser.add_argument(
        "--generate-max-workers", type=int, help="Optional generate max_workers override."
    )
    teacher_parser.add_argument(
        "--generate-batch-size", type=int, help="Optional generate batch_size override."
    )
    teacher_parser.add_argument(
        "--skip-render-ppt",
        action="store_true",
        help="Skip PPT rendering and only produce parser/generate artifacts.",
    )
    return parser


def _run_teacher_workflow_command(args: argparse.Namespace) -> int:
    request_path = Path(args.request_file)
    if not request_path.exists():
        raise FileNotFoundError(f"Teacher workflow request file does not exist: {request_path}")

    teacher_request = json.loads(request_path.read_text(encoding="utf-8"))
    result = run_teacher_workflow(
        teacher_request,
        parser_log_file=args.parser_log_file,
        generate_log_file=args.generate_log_file,
        artifact_file=args.artifact_file,
        rendered_ppt_file=args.rendered_ppt_file,
        env_path=args.env_path,
        parser_max_workers=args.parser_max_workers,
        parser_batch_size=args.parser_batch_size,
        generate_max_sections=args.generate_max_sections,
        generate_max_workers=args.generate_max_workers,
        generate_batch_size=args.generate_batch_size,
        render_ppt=not args.skip_render_ppt,
    )

    output_path = Path(args.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
