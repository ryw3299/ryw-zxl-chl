"""
courseware_flash_render.py - slide_plan.json -> rendered PPTX (L3 entry).

This is the backend-facing entry function for the deterministic rendering
half of the courseware-flash pipeline. Unlike
``run_courseware_flash_slideplan()``, this stage does not call Claude. Its
responsibility is:

    slide_plan.json
         |
         v
    validate_slide_plan.py
         |
         v
    render_from_plan.py
         |
         v
    total_md_split.py
         |
         v
    finalize_svg.py
         |
         v
    svg_to_pptx.py
         |
         v
    exports/*.pptx

The intended backend usage is:
1. Call ``run_courseware_flash_slideplan()`` to create ``slide_plan.json``.
2. Let the user edit the JSON in place.
3. Call ``run_courseware_flash_render()`` against the same project directory.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Optional

from src.agents._courseware_runtime import (
    COURSEWARE_FLASH_SCRIPTS_DIR,
    PPT_MASTER_SCRIPTS_DIR,
    get_courseware_logger,
    load_courseware_env,
)

VALIDATE_SLIDE_PLAN_SCRIPT = COURSEWARE_FLASH_SCRIPTS_DIR / "validate_slide_plan.py"
RENDER_FROM_PLAN_SCRIPT = COURSEWARE_FLASH_SCRIPTS_DIR / "render_from_plan.py"
SVG_QUALITY_CHECKER_SCRIPT = PPT_MASTER_SCRIPTS_DIR / "svg_quality_checker.py"
TOTAL_MD_SPLIT_SCRIPT = PPT_MASTER_SCRIPTS_DIR / "total_md_split.py"
FINALIZE_SVG_SCRIPT = PPT_MASTER_SCRIPTS_DIR / "finalize_svg.py"
SVG_TO_PPTX_SCRIPT = PPT_MASTER_SCRIPTS_DIR / "svg_to_pptx.py"


async def run_courseware_flash_render(
    project_dir: Optional[str | Path] = None,
    slide_plan_path: Optional[str | Path] = None,
    log_file: Optional[str] = None,
    env_path: Optional[str] = None,
    run_quality_check: bool = True,
    timeout: float = 600.0,
) -> dict[str, Any]:
    """Render a previously prepared ``slide_plan.json`` into SVG/PPTX artifacts.

    Args:
        project_dir: Project directory containing ``slide_plan.json``.
        slide_plan_path: Explicit ``slide_plan.json`` path. If given,
            ``project_dir`` is inferred from its parent unless also set.
        log_file: Optional log file path for the structured logger.
        env_path: Optional .env override; defaults to ``<PROJECT_ROOT>/.env``.
        run_quality_check: Run ``svg_quality_checker.py`` after SVG rendering.
        timeout: Per-step subprocess timeout in seconds.

    Returns:
        A dict with artifact locations for backend consumption.

    Raises:
        ValueError: Neither ``project_dir`` nor ``slide_plan_path`` is provided.
        FileNotFoundError: Required project files are missing.
        RuntimeError: Any render/export subprocess fails.
    """
    load_courseware_env(env_path)

    logger = get_courseware_logger("chaoxing.courseware_flash_render", log_file=log_file)
    runtime_log_path = getattr(logger, "runtime_log_path", None)

    project_path, resolved_slide_plan = _resolve_project_inputs(
        project_dir=project_dir,
        slide_plan_path=slide_plan_path,
    )
    logger.info("Starting courseware_flash render pipeline")
    logger.info("Project directory: %s", project_path)
    logger.info("slide_plan.json: %s", resolved_slide_plan)

    if not resolved_slide_plan.exists():
        raise FileNotFoundError(f"slide_plan.json not found: {resolved_slide_plan}")

    step_outputs: dict[str, str] = {}

    step_outputs["validate"] = await _run_step(
        name="validate_slide_plan",
        script_path=VALIDATE_SLIDE_PLAN_SCRIPT,
        args=[str(project_path)],
        logger=logger,
        timeout=timeout,
    )

    step_outputs["render"] = await _run_step(
        name="render_from_plan",
        script_path=RENDER_FROM_PLAN_SCRIPT,
        args=[str(project_path)],
        logger=logger,
        timeout=timeout,
    )

    if run_quality_check:
        step_outputs["quality_check"] = await _run_step(
            name="svg_quality_checker",
            script_path=SVG_QUALITY_CHECKER_SCRIPT,
            args=[str(project_path)],
            logger=logger,
            timeout=timeout,
        )

    step_outputs["split_notes"] = await _run_step(
        name="total_md_split",
        script_path=TOTAL_MD_SPLIT_SCRIPT,
        args=[str(project_path)],
        logger=logger,
        timeout=timeout,
    )

    step_outputs["finalize_svg"] = await _run_step(
        name="finalize_svg",
        script_path=FINALIZE_SVG_SCRIPT,
        args=[str(project_path)],
        logger=logger,
        timeout=timeout,
    )

    step_outputs["svg_to_pptx"] = await _run_step(
        name="svg_to_pptx",
        script_path=SVG_TO_PPTX_SCRIPT,
        args=[str(project_path)],
        logger=logger,
        timeout=timeout,
    )

    svg_output_dir = project_path / "svg_output"
    svg_final_dir = project_path / "svg_final"
    notes_dir = project_path / "notes"
    exports_dir = project_path / "exports"
    backup_root = project_path / "backup"

    if not svg_output_dir.exists():
        raise RuntimeError(f"svg_output not found after render: {svg_output_dir}")
    if not exports_dir.exists():
        raise RuntimeError(f"exports directory not found after pptx export: {exports_dir}")

    exported_pptx = _find_latest_pptx(exports_dir)
    if exported_pptx is None:
        raise RuntimeError(f"No PPTX found in exports directory: {exports_dir}")

    backup_dir = _find_latest_backup_dir(backup_root)

    logger.info("Render pipeline complete. PPTX: %s", exported_pptx)

    return {
        "status": "success",
        "project_dir": str(project_path),
        "slide_plan_path": str(resolved_slide_plan),
        "svg_output_dir": str(svg_output_dir),
        "svg_final_dir": str(svg_final_dir) if svg_final_dir.exists() else None,
        "notes_dir": str(notes_dir) if notes_dir.exists() else None,
        "exports_dir": str(exports_dir),
        "pptx_path": str(exported_pptx),
        "backup_dir": str(backup_dir) if backup_dir else None,
        "log_file": runtime_log_path,
        "step_outputs": step_outputs,
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


async def _run_step(
    name: str,
    script_path: Path,
    args: list[str],
    logger,
    timeout: float,
) -> str:
    """Execute one Python script step and return combined stdout text."""
    if not script_path.exists():
        raise FileNotFoundError(f"Required script not found: {script_path}")

    logger.info("Running step %s: %s %s", name, script_path, " ".join(args))
    child_env = os.environ.copy()
    child_env.setdefault("PYTHONIOENCODING", "utf-8")
    child_env.setdefault("PYTHONUTF8", "1")
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(script_path),
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=child_env,
    )

    try:
        stdout_b, stderr_b = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except TimeoutError as exc:
        process.kill()
        await process.communicate()
        raise RuntimeError(f"{name} timed out after {timeout:.1f}s while running {script_path}") from exc

    stdout = stdout_b.decode("utf-8", errors="replace") if stdout_b else ""
    stderr = stderr_b.decode("utf-8", errors="replace") if stderr_b else ""

    if stdout:
        logger.info("%s stdout:\n%s", name, stdout)
    if stderr:
        logger.info("%s stderr:\n%s", name, stderr)

    if process.returncode != 0:
        raise RuntimeError(f"{name} failed (rc={process.returncode}). stdout:\n{stdout}\nstderr:\n{stderr}")

    return stdout.strip()


def _find_latest_pptx(exports_dir: Path) -> Optional[Path]:
    """Return the newest exported PPTX under exports/."""
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
