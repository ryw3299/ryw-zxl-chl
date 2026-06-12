import json
from pathlib import Path
from typing import Optional

from src.agents.file_parser import build_file_parser_stages
from src.agents.generate import build_generate_stages
from src.utils.logging_utils import resolve_runtime_output_path
from src.utils.renderers import render_ppt_outline


def run_teacher_workflow(
    teacher_input: dict,
    *,
    parser_log_file: Optional[str] = None,
    generate_log_file: Optional[str] = None,
    artifact_file: Optional[str] = None,
    rendered_ppt_file: Optional[str] = None,
    parser_llm_callable=None,
    generate_llm_callable=None,
    env_path: Optional[str] = None,
    parser_max_workers: Optional[int] = None,
    parser_batch_size: Optional[int] = None,
    generate_max_sections: Optional[int] = None,
    generate_max_workers: Optional[int] = None,
    generate_batch_size: Optional[int] = None,
    render_ppt: bool = True,
) -> dict:
    stages = build_teacher_workflow_stages(
        teacher_input,
        parser_log_file=parser_log_file,
        generate_log_file=generate_log_file,
        artifact_file=artifact_file,
        rendered_ppt_file=rendered_ppt_file,
        parser_llm_callable=parser_llm_callable,
        generate_llm_callable=generate_llm_callable,
        env_path=env_path,
        parser_max_workers=parser_max_workers,
        parser_batch_size=parser_batch_size,
        generate_max_sections=generate_max_sections,
        generate_max_workers=generate_max_workers,
        generate_batch_size=generate_batch_size,
        render_ppt=render_ppt,
    )
    return stages["output"]


def build_teacher_workflow_stages(
    teacher_input: dict,
    *,
    parser_log_file: Optional[str] = None,
    generate_log_file: Optional[str] = None,
    artifact_file: Optional[str] = None,
    rendered_ppt_file: Optional[str] = None,
    parser_llm_callable=None,
    generate_llm_callable=None,
    env_path: Optional[str] = None,
    parser_max_workers: Optional[int] = None,
    parser_batch_size: Optional[int] = None,
    generate_max_sections: Optional[int] = None,
    generate_max_workers: Optional[int] = None,
    generate_batch_size: Optional[int] = None,
    render_ppt: bool = True,
) -> dict:
    request = _normalize_teacher_input(teacher_input)

    parser_request = {
        "course_id": request["course_id"],
        "lesson_id": request["lesson_id"],
        "assets": request["assets"],
        "parse_instruction": request["parse_instruction"],
    }
    parser_stages = build_file_parser_stages(
        parser_request,
        log_file=parser_log_file,
        llm_callable=parser_llm_callable,
        env_path=env_path,
        max_workers=parser_max_workers,
        batch_size=parser_batch_size,
    )

    generate_request = {
        "course_id": request["course_id"],
        "lesson_id": request["lesson_id"],
        "lesson_name": request["lesson_name"],
        "structured_content": parser_stages["structured_content"].model_dump(mode="python"),
        "teacher_notes": request["teacher_notes"],
        "generate_instruction": request["generate_instruction"],
    }
    generate_stages = build_generate_stages(
        generate_request,
        log_file=generate_log_file,
        llm_callable=generate_llm_callable,
        env_path=env_path,
        max_sections=generate_max_sections,
        max_workers=generate_max_workers,
        batch_size=generate_batch_size,
    )

    rendered_ppt_path = None
    render_error = None
    if render_ppt:
        try:
            requested_render_path = rendered_ppt_file or _default_render_path(request["lesson_id"])
            rendered_ppt_path = render_ppt_outline(
                ppt_outline=generate_stages["ppt_outline"],
                lesson_script=generate_stages["lesson_script"],
                source_assets=parser_stages["output"].source_assets,
                source_pages=parser_stages["output"].pages,
                output_path=requested_render_path,
            )
        except Exception as exc:
            render_error = str(exc)

    artifact_path = _write_teacher_artifact(
        artifact_file=artifact_file,
        request=request,
        parser_stages=parser_stages,
        generate_stages=generate_stages,
        rendered_ppt_path=rendered_ppt_path,
        render_error=render_error,
        parser_max_workers=parser_max_workers,
        parser_batch_size=parser_batch_size,
        generate_max_sections=generate_max_sections,
        generate_max_workers=generate_max_workers,
        generate_batch_size=generate_batch_size,
        render_ppt=render_ppt,
    )

    parser_output = parser_stages["output"].model_dump(mode="python")
    generate_output = generate_stages["output"].model_dump(mode="python")
    output = {
        "status": "success",
        "message": "teacher workflow finished",
        "course_id": request["course_id"],
        "lesson_id": request["lesson_id"],
        "lesson_name": request["lesson_name"],
        "parser_output": parser_output,
        "generate_output": generate_output,
        "rendered_ppt_file": str(rendered_ppt_path) if rendered_ppt_path else None,
        "artifact_file": str(artifact_path) if artifact_path else None,
        "metadata": {
            "parser_log_file": parser_output.get("metadata", {}).get("log_file"),
            "generate_log_file": generate_output.get("metadata", {}).get("log_file"),
            "render_ppt_requested": render_ppt,
            "render_ppt_succeeded": rendered_ppt_path is not None,
            "render_error": render_error,
        },
    }

    return {
        "request": request,
        "parser_request": parser_request,
        "parser_stages": parser_stages,
        "generate_request": generate_request,
        "generate_stages": generate_stages,
        "rendered_ppt_path": rendered_ppt_path,
        "artifact_path": artifact_path,
        "output": output,
    }


def _normalize_teacher_input(teacher_input: dict) -> dict:
    assets = list(teacher_input.get("assets") or [])
    if not assets:
        raise ValueError("teacher workflow requires at least one asset.")

    lesson_id = (teacher_input.get("lesson_id") or "").strip()
    if not lesson_id:
        raise ValueError("teacher workflow requires lesson_id.")

    first_file_name = str(assets[0].get("file_name") or Path(str(assets[0]["file_path"])).stem)
    lesson_name = (teacher_input.get("lesson_name") or "").strip() or Path(first_file_name).stem

    return {
        "course_id": _normalize_optional(teacher_input.get("course_id")),
        "lesson_id": lesson_id,
        "lesson_name": lesson_name,
        "assets": assets,
        "parse_instruction": _normalize_optional(teacher_input.get("parse_instruction")),
        "teacher_notes": _normalize_optional(teacher_input.get("teacher_notes")) or "",
        "generate_instruction": _normalize_optional(teacher_input.get("generate_instruction")) or "",
    }


def _write_teacher_artifact(
    *,
    artifact_file: Optional[str],
    request: dict,
    parser_stages: dict,
    generate_stages: dict,
    rendered_ppt_path: Optional[Path],
    render_error: Optional[str],
    parser_max_workers: Optional[int],
    parser_batch_size: Optional[int],
    generate_max_sections: Optional[int],
    generate_max_workers: Optional[int],
    generate_batch_size: Optional[int],
    render_ppt: bool,
) -> Optional[Path]:
    if not artifact_file:
        return None

    artifact_path = resolve_runtime_output_path(artifact_file)
    if artifact_path is None:
        raise RuntimeError("Artifact path resolution failed.")

    payload = {
        "workflow_request": request,
        "workflow_config": {
            "parser_max_workers": parser_max_workers,
            "parser_batch_size": parser_batch_size,
            "generate_max_sections": generate_max_sections,
            "generate_max_workers": generate_max_workers,
            "generate_batch_size": generate_batch_size,
            "render_ppt": render_ppt,
        },
        "parser_request": parser_stages["request"].model_dump(mode="python"),
        "parser_output": parser_stages["output"].model_dump(mode="python"),
        "generate_request": generate_stages["request"].model_dump(mode="python"),
        "generate_output": generate_stages["output"].model_dump(mode="python"),
        "rendered_ppt_file": str(rendered_ppt_path) if rendered_ppt_path else None,
        "render_error": render_error,
    }
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return artifact_path


def _default_render_path(lesson_id: str) -> str:
    return str(Path("tests") / "logs" / "generate" / "manual" / f"{lesson_id}_teacher_workflow.pptx")


def _normalize_optional(value) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None
