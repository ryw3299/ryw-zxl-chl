"""
courseware_pro_render.py - slide_plan.json -> agent-driven render/export.

This is the backend-facing "pro" second-stage entry. It assumes the project
already contains a user-reviewable ``slide_plan.json`` and optionally
``sources/*.md`` and ``images/manifest.json`` from the earlier flash phase.

Unlike ``run_courseware_flash_render()``, this stage intentionally gives a
Claude agent controlled autonomy over the post-plan workflow:

    existing slide_plan.json
          |
          v
    agent reads project state
          |
          v
    agent validates / minimally repairs slide_plan.json if needed
          |
          v
    agent runs render_from_plan -> total_md_split -> finalize_svg -> svg_to_pptx
          |
          v
    optional agent-generated narrations

The key contract is:
- Phase 1 remains deterministic and user-reviewable (`slide_plan.json`)
- Phase 2 is fully automated by the Claude SDK agent
- The agent may fix rendering issues, but should not redesign the courseware
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from src.agents._courseware_runtime import (
    CLAUDE_SDK_ROOT,
    COURSEWARE_FLASH_DIR,
    DETAIL_LEVELS,
    PPT_MASTER_SCRIPTS_DIR,
    get_courseware_logger,
    load_courseware_env,
)


async def run_courseware_pro_render(
    project_dir: Optional[str | Path] = None,
    slide_plan_path: Optional[str | Path] = None,
    audience: str = "",
    log_file: Optional[str] = None,
    env_path: Optional[str] = None,
    provider: str = "xfyun",
    timeout: float = 1200.0,
    generate_narration: bool = False,
) -> dict[str, Any]:
    """Run the agent-driven post-slide-plan workflow.

    Args:
        project_dir: Project directory containing slide_plan.json.
        slide_plan_path: Explicit slide_plan.json path.
        audience: Optional audience hint for optional narration generation.
        log_file: Optional structured logger file path.
        env_path: Optional .env override; defaults to <PROJECT_ROOT>/.env.
        provider: AgentFactory provider key (default "xfyun").
        timeout: Per-attempt agent timeout in seconds.
        generate_narration: Whether the agent should also create
            narration_A/B/C/D.json after PPTX export.

    Returns:
        Dict with project paths and generated artifacts.
    """
    from claude_sdk.infra.agent_factory import AgentFactory  # noqa: WPS433

    load_courseware_env(env_path)

    logger = get_courseware_logger("chaoxing.courseware_pro_render", log_file=log_file)
    runtime_log_path = getattr(logger, "runtime_log_path", None)

    project_path, resolved_slide_plan = _resolve_project_inputs(
        project_dir=project_dir,
        slide_plan_path=slide_plan_path,
    )
    logger.info("Starting courseware_pro render pipeline")
    logger.info("Project directory: %s", project_path)
    logger.info("slide_plan.json: %s", resolved_slide_plan)

    if not resolved_slide_plan.exists():
        raise FileNotFoundError(f"slide_plan.json not found: {resolved_slide_plan}")

    plan = json.loads(resolved_slide_plan.read_text(encoding="utf-8"))
    slide_count = len(plan.get("slides", []))

    agent = AgentFactory.create_agent(
        agent_name="courseware_pro_render",
        skills=["courseware_pro_render"],
        cwd=str(project_path),
        workspace=str(project_path),
        project_root=str(CLAUDE_SDK_ROOT),
        provider=provider,
        tools=["Bash", "Read", "Edit", "Write", "Glob"],
        permission_mode="acceptEdits",
    )

    prompt = _build_pro_render_prompt(
        project_path=project_path,
        slide_plan_path=resolved_slide_plan,
        audience=audience,
        generate_narration=generate_narration,
    )

    await agent.start()
    try:
        agent_response = await agent.ask_with_retry(prompt, timeout=timeout)

        max_repair_attempts = 2
        last_error: Optional[str] = None
        for attempt in range(max_repair_attempts + 1):
            validation_error = _validate_pro_outputs(
                project_dir=project_path,
                expected_slide_count=slide_count,
                expect_narration=generate_narration,
            )
            if validation_error is None:
                last_error = None
                break

            last_error = validation_error
            logger.warning(
                "courseware_pro outputs invalid (attempt %d/%d): %s",
                attempt + 1,
                max_repair_attempts + 1,
                validation_error,
            )
            if attempt >= max_repair_attempts:
                break

            repair_prompt = _build_pro_repair_prompt(
                project_path=project_path,
                slide_plan_path=resolved_slide_plan,
                validation_error=validation_error,
                generate_narration=generate_narration,
            )
            agent_response = await agent.ask_with_retry(repair_prompt, timeout=timeout)

        if last_error is not None:
            raise RuntimeError(
                f"courseware_pro render did not complete successfully after "
                f"{max_repair_attempts + 1} attempts: {last_error}. "
                f"Agent response: {agent_response[:500]}"
            )
    finally:
        await agent.close()

    exports_dir = project_path / "exports"
    backup_dir = _find_latest_backup_dir(project_path / "backup")
    narration_paths = (
        {level: str(project_path / f"narration_{level}.json") for level in DETAIL_LEVELS}
        if generate_narration
        else None
    )

    return {
        "status": "success",
        "project_dir": str(project_path),
        "slide_plan_path": str(resolved_slide_plan),
        "svg_output_dir": str(project_path / "svg_output"),
        "svg_final_dir": str(project_path / "svg_final") if (project_path / "svg_final").exists() else None,
        "notes_dir": str(project_path / "notes") if (project_path / "notes").exists() else None,
        "exports_dir": str(exports_dir) if exports_dir.exists() else None,
        "pptx_path": str(_find_latest_pptx(exports_dir)) if exports_dir.exists() else None,
        "backup_dir": str(backup_dir) if backup_dir else None,
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


def _build_pro_render_prompt(
    project_path: Path,
    slide_plan_path: Path,
    audience: str,
    generate_narration: bool,
) -> str:
    """Build the task prompt for the pro render agent."""
    parts: list[str] = [
        "Your task is to continue from an existing slide_plan.json and finish the full post-plan pipeline.",
        "Do not rerun source conversion. Do not redesign the courseware from scratch.",
        "",
        f"Project directory: {project_path}",
        f"slide_plan.json path: {slide_plan_path}",
        f"Courseware Flash scripts: {COURSEWARE_FLASH_DIR / 'scripts'}",
        f"PPT Master scripts: {PPT_MASTER_SCRIPTS_DIR}",
    ]

    sources_dir = project_path / "sources"
    images_manifest = project_path / "images" / "manifest.json"
    if sources_dir.exists():
        parts.append(f"sources directory: {sources_dir}")
    if images_manifest.exists():
        parts.append(f"images manifest: {images_manifest}")
    if audience:
        parts.append(f"target audience: {audience}")

    parts.extend(
        [
            "",
            "Workflow you must execute:",
            "1. Read slide_plan.json and inspect the current project state.",
            "2. If slide_plan.json has schema or rendering compatibility issues, fix it with the smallest possible edits.",
            "3. Run validate_slide_plan.py against the project directory.",
            "4. Run render_from_plan.py to produce svg_output.",
            "5. Run svg_quality_checker.py and react to the findings if they block export.",
            "6. Run total_md_split.py.",
            "7. Run finalize_svg.py.",
            "8. Run svg_to_pptx.py and confirm that exports/*.pptx exists.",
        ]
    )

    if generate_narration:
        parts.extend(
            [
                "9. After PPTX export, generate narration_A/B/C/D.json in the project directory.",
                "   - A: most detailed, around 400 Chinese characters per slide",
                "   - B: detailed, around 250 Chinese characters per slide",
                "   - C: concise, around 150 Chinese characters per slide",
                "   - D: shortest, around 80 Chinese characters per slide",
            ]
        )

    parts.extend(
        [
            "",
            "Hard rules:",
            "- Use the existing slide_plan.json as the source of truth.",
            "- You may repair slide_plan.json, but only to make validation / rendering / export succeed.",
            "- Do not change the teaching structure, slide count, chapter order, or learning goals unless strictly necessary for fixing a concrete failure.",
            "- Do not rerun auto_source_convert.py or regenerate a new slide plan from the source files.",
            "- Use Bash / Read / Edit / Write / Glob tools as needed.",
            "- If a step fails, diagnose it, apply the minimum viable fix, and retry.",
            "- Final response must summarize what you changed and list the final artifact paths.",
        ]
    )

    return "\n".join(parts)


def _validate_pro_outputs(
    project_dir: Path,
    expected_slide_count: int,
    expect_narration: bool,
) -> Optional[str]:
    """Check that the agent finished the expected artifact set."""
    slide_plan_path = project_dir / "slide_plan.json"
    try:
        plan = json.loads(slide_plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return (
            f"slide_plan.json is not valid JSON after agent execution: "
            f"{exc.msg} at line {exc.lineno} col {exc.colno}"
        )

    slides = plan.get("slides")
    if not isinstance(slides, list) or len(slides) != expected_slide_count:
        return (
            f"slide_plan.json slide count changed unexpectedly: "
            f"expected {expected_slide_count}, got {len(slides) if isinstance(slides, list) else 'invalid'}"
        )

    svg_output_dir = project_dir / "svg_output"
    if not svg_output_dir.exists():
        return "svg_output directory was not generated"

    exports_dir = project_dir / "exports"
    if not exports_dir.exists():
        return "exports directory was not generated"

    pptx_path = _find_latest_pptx(exports_dir)
    if pptx_path is None:
        return "No PPTX file exists under exports/"

    if expect_narration:
        for level in DETAIL_LEVELS:
            path = project_dir / f"narration_{level}.json"
            if not path.exists():
                return f"Missing narration file: {path.name}"
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                return f"{path.name} is not valid JSON: {exc.msg} at line {exc.lineno} col {exc.colno}"
            if data.get("detail_level") != level:
                return f"{path.name} has detail_level={data.get('detail_level')!r}, expected {level!r}"

    return None


def _build_pro_repair_prompt(
    project_path: Path,
    slide_plan_path: Path,
    validation_error: str,
    generate_narration: bool,
) -> str:
    """Build a targeted retry prompt after artifact validation fails."""
    parts = [
        "The previous run did not complete successfully. Repair the existing project in place.",
        f"Project directory: {project_path}",
        f"slide_plan.json path: {slide_plan_path}",
        f"Observed failure: {validation_error}",
        "",
        "Repair rules:",
        "- Read the relevant files and inspect the actual project state.",
        "- Apply only the minimum changes needed to resolve the reported failure.",
        "- Re-run the necessary downstream commands, not the whole pipeline unless needed.",
        "- Do not redesign the courseware or regenerate source conversion artifacts.",
    ]
    if generate_narration:
        parts.append(
            "- If PPTX export is already successful, only repair the missing or invalid narration outputs."
        )
    parts.append("Final response: briefly state the fix and the resulting artifact paths.")
    return "\n".join(parts)


def _find_latest_pptx(exports_dir: Path) -> Optional[Path]:
    """Return the newest exported PPTX under exports/."""
    if not exports_dir.exists():
        return None
    candidates = sorted(
        exports_dir.glob("*.pptx"),
        key=lambda path: path.stat().st_mtime,
    )
    return candidates[-1] if candidates else None


def _find_latest_backup_dir(backup_root: Path) -> Optional[Path]:
    """Return the newest timestamped backup directory under backup/."""
    if not backup_root.exists():
        return None
    candidates = sorted(
        [path for path in backup_root.iterdir() if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
    )
    return candidates[-1] if candidates else None
