"""
courseware_flash_narration.py - slide_plan.json -> narration_A/B/C/D.json.

Backend-facing narration entry for the courseware-flash pipeline. This stage
uses Claude to expand a finalized ``slide_plan.json`` into four narration
variants with different detail levels:

    A: most detailed
    B: detailed
    C: concise
    D: shortest

Intended backend flow:
1. Generate ``slide_plan.json`` with ``run_courseware_flash_slideplan()``.
2. Let the user edit the slide plan in place.
3. Optionally render the PPTX with ``run_courseware_flash_render()``.
4. Generate narrations from the edited slide plan with
   ``run_courseware_flash_narration()``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from src.agents._courseware_runtime import (
    CLAUDE_SDK_ROOT,
    DETAIL_LEVELS,
    get_courseware_logger,
    load_courseware_env,
)


async def run_courseware_flash_narration(
    project_dir: Optional[str | Path] = None,
    slide_plan_path: Optional[str | Path] = None,
    output_dir: Optional[str | Path] = None,
    audience: str = "",
    log_file: Optional[str] = None,
    env_path: Optional[str] = None,
    provider: str = "xfyun",
    timeout: float = 900.0,
) -> dict[str, Any]:
    """Generate narration_A/B/C/D.json from slide_plan.json.

    Args:
        project_dir: Project directory containing slide_plan.json.
        slide_plan_path: Explicit slide_plan.json path.
        output_dir: Directory for narration JSON outputs. Defaults to the same
            directory as slide_plan.json.
        audience: Optional target audience hint for narration tone/depth.
        log_file: Optional structured logger file path.
        env_path: Optional .env override; defaults to <PROJECT_ROOT>/.env.
        provider: AgentFactory provider key (default "xfyun").
        timeout: Per-attempt agent ask timeout in seconds.

    Returns:
        Dict with narration output paths for backend consumption.

    Raises:
        ValueError: Neither project_dir nor slide_plan_path is provided.
        FileNotFoundError: slide_plan.json is missing.
        RuntimeError: Agent fails to generate valid JSON outputs.
    """
    from claude_sdk.infra.agent_factory import AgentFactory  # noqa: WPS433

    load_courseware_env(env_path)

    logger = get_courseware_logger("chaoxing.courseware_flash_narration", log_file=log_file)
    runtime_log_path = getattr(logger, "runtime_log_path", None)

    project_path, resolved_slide_plan = _resolve_project_inputs(
        project_dir=project_dir,
        slide_plan_path=slide_plan_path,
    )
    narration_dir = Path(output_dir).resolve() if output_dir else resolved_slide_plan.parent
    narration_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting courseware_flash narration pipeline")
    logger.info("Project directory: %s", project_path)
    logger.info("slide_plan.json: %s", resolved_slide_plan)
    logger.info("Narration output directory: %s", narration_dir)

    if not resolved_slide_plan.exists():
        raise FileNotFoundError(f"slide_plan.json not found: {resolved_slide_plan}")

    plan = json.loads(resolved_slide_plan.read_text(encoding="utf-8"))
    slide_count = len(plan.get("slides", []))

    agent = AgentFactory.create_agent(
        agent_name="narration_from_ppt",
        skills=["narration_from_ppt"],
        cwd=str(project_path),
        workspace=str(narration_dir),
        project_root=str(CLAUDE_SDK_ROOT),
        provider=provider,
        tools=["Read", "Write", "Edit"],
        permission_mode="acceptEdits",
    )

    prompt = _build_narration_prompt(
        slide_plan_path=resolved_slide_plan,
        output_dir=narration_dir,
        audience=audience,
        plan=plan,
    )

    await agent.start()
    try:
        agent_response = await agent.ask_with_retry(prompt, timeout=timeout)

        max_repair_attempts = 2
        last_error: Optional[str] = None
        for attempt in range(max_repair_attempts + 1):
            validation_error = _validate_narration_outputs(
                output_dir=narration_dir,
                expected_slide_count=slide_count,
                deck_title=plan.get("deck_title", ""),
            )
            if validation_error is None:
                last_error = None
                break

            last_error = validation_error
            logger.warning(
                "Narration outputs invalid (attempt %d/%d): %s",
                attempt + 1,
                max_repair_attempts + 1,
                validation_error,
            )
            if attempt >= max_repair_attempts:
                break

            repair_prompt = _build_narration_repair_prompt(
                slide_plan_path=resolved_slide_plan,
                output_dir=narration_dir,
                validation_error=validation_error,
            )
            agent_response = await agent.ask_with_retry(repair_prompt, timeout=timeout)

        if last_error is not None:
            raise RuntimeError(
                f"Narration outputs remain invalid after {max_repair_attempts + 1} attempts: "
                f"{last_error}. Agent response: {agent_response[:500]}"
            )
    finally:
        await agent.close()

    narration_paths = {level: str(narration_dir / f"narration_{level}.json") for level in DETAIL_LEVELS}
    logger.info("Narration generation complete: %s", narration_paths)

    return {
        "status": "success",
        "project_dir": str(project_path),
        "slide_plan_path": str(resolved_slide_plan),
        "output_dir": str(narration_dir),
        "audience": audience,
        "narration_paths": narration_paths,
        "log_file": runtime_log_path,
        "agent_response": agent_response,
    }


def _resolve_project_inputs(
    project_dir: Optional[str | Path],
    slide_plan_path: Optional[str | Path],
) -> tuple[Path, Path]:
    """Resolve project_dir and slide_plan.json path from caller inputs."""
    if project_dir is None and slide_plan_path is None:
        raise ValueError("Either project_dir or slide_plan_path must be provided.")

    resolved_project_dir: Optional[Path] = None
    resolved_slide_plan: Optional[Path] = None

    if slide_plan_path is not None:
        resolved_slide_plan = Path(slide_plan_path).resolve()
        resolved_project_dir = resolved_slide_plan.parent

    if project_dir is not None:
        resolved_project_dir = Path(project_dir).resolve()
        if resolved_slide_plan is None:
            resolved_slide_plan = resolved_project_dir / "slide_plan.json"

    assert resolved_project_dir is not None
    assert resolved_slide_plan is not None

    if not resolved_project_dir.exists():
        raise FileNotFoundError(f"Project directory not found: {resolved_project_dir}")

    return resolved_project_dir, resolved_slide_plan


def _build_narration_prompt(
    slide_plan_path: Path,
    output_dir: Path,
    audience: str,
    plan: dict[str, Any],
) -> str:
    """Compose the per-call prompt for narration generation."""
    deck_title = plan.get("deck_title", "Unnamed Courseware")
    slides = plan.get("slides", [])
    slides_summary = [
        f"Slide {slide.get('slide_id')}: [{slide.get('type')}] {slide.get('title', '')}" for slide in slides
    ]

    parts: list[str] = [
        "你的本次任务:基于既有 slide_plan.json 生成四个讲稿文件,不要修改 slide_plan.json 本身。",
        "",
        f"课件标题:{deck_title}",
        f"总页数:{len(slides)}",
        f"slide_plan.json 路径:{slide_plan_path}",
        f"讲稿输出目录:{output_dir}",
    ]
    if audience:
        parts.append(f"目标受众:{audience}")

    parts.extend(
        [
            "",
            "页面概览:",
            *slides_summary,
            "",
            "输出文件要求:",
            f"- 写入 {output_dir / 'narration_A.json'} : A档,最详细,约400字/页",
            f"- 写入 {output_dir / 'narration_B.json'} : B档,详细,约250字/页",
            f"- 写入 {output_dir / 'narration_C.json'} : C档,简要,约150字/页",
            f"- 写入 {output_dir / 'narration_D.json'} : D档,最略,约80字/页",
            "",
            "硬约束:",
            "- 必须先 Read slide_plan.json,再生成讲稿。",
            "- 必须实际用 Write 工具把四个 JSON 文件写到输出目录。",
            "- 四个档位都必须覆盖全部 slide,slide_id 必须和 slide_plan.json 对齐。",
            "- topic 直接取 slide_plan.json 中每页的 title。",
            "- 只生成讲稿 JSON,不要生成 markdown,不要输出额外说明文件。",
            "- 完成后只回一句:已完成。",
        ]
    )

    return "\n".join(parts)


def _validate_narration_outputs(
    output_dir: Path,
    expected_slide_count: int,
    deck_title: str,
) -> Optional[str]:
    """Validate that A/B/C/D narration files all exist and are parseable."""
    for level in DETAIL_LEVELS:
        path = output_dir / f"narration_{level}.json"
        if not path.exists():
            return f"Missing output file: {path.name}"

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return f"{path.name} is not valid JSON: {exc.msg} at line {exc.lineno} col {exc.colno}"

        if data.get("detail_level") != level:
            return f"{path.name} has detail_level={data.get('detail_level')!r}, expected {level!r}"
        if data.get("total_slides") != expected_slide_count:
            return (
                f"{path.name} has total_slides={data.get('total_slides')!r}, expected {expected_slide_count}"
            )
        if deck_title and data.get("deck_title") != deck_title:
            return f"{path.name} has deck_title mismatch"

        slides = data.get("slides")
        if not isinstance(slides, list):
            return f"{path.name} field 'slides' must be a list"
        if len(slides) != expected_slide_count:
            return f"{path.name} contains {len(slides)} slide scripts, expected {expected_slide_count}"

        for item in slides:
            if not isinstance(item, dict):
                return f"{path.name} contains a non-object slide entry"
            if "slide_id" not in item or "topic" not in item or "script" not in item:
                return f"{path.name} has slide entries missing slide_id/topic/script"

    return None


def _build_narration_repair_prompt(
    slide_plan_path: Path,
    output_dir: Path,
    validation_error: str,
) -> str:
    """Compose a targeted repair prompt for narration outputs."""
    parts = [
        "刚才生成的讲稿文件不符合要求,请修复现有文件,不要重写无关内容。",
        f"错误:{validation_error}",
        f"slide_plan.json 路径:{slide_plan_path}",
        f"讲稿输出目录:{output_dir}",
        "",
        "修复要求:",
        "- 先 Read 出错的讲稿文件和 slide_plan.json。",
        "- 只修复缺失文件、JSON 语法、detail_level、total_slides 或 slides 对齐问题。",
        "- topic 继续直接取 slide_plan.json 的 title。",
        "- 修完后用 Write 或 Edit 落盘到原文件路径。",
        "- 完成后只回一句:已修复。",
    ]
    return "\n".join(parts)
