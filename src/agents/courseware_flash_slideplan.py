"""
courseware_flash_slideplan.py — material -> slide_plan.json (L3 entry).

This is the backend-facing entry function for Phase A + Phase B of the
courseware-flash pipeline. It does NOT render SVG/PPTX and does NOT
generate narrations. Its sole responsibility is:

    (optional) material file
            |
            v
    Phase A: ppt-master/skills/courseware-flash/scripts/auto_source_convert.py
            -> <project_dir>/sources/<stem>.md
            -> <project_dir>/images/*.png + images/manifest.json
            |
            v
    Phase B: AgentFactory("courseware_flash") generates
            -> <project_dir>/slide_plan.json

Artifact layout (matches `src/claude_agents/courseware_flash.py`):

    <workspace_root>/projects/<YYYYMMDD_HHMMSS>_<uuid8>/
        sources/<stem>.md
        images/<stem>_p*.png + images/manifest.json
        slide_plan.json
        courseware_flash.log  (agent transcript)

When the caller does not supply `project_dir`, the function generates the
timestamped subdirectory itself so the backend can simply pick the path
out of the returned dict and read / edit `slide_plan.json` in place.

Inputs / outputs are intentionally unstructured (plain dict / str) so the
backend can wrap them. Only slide_plan.json has a fixed schema (enforced
by the agent's system_prompt + skill yaml).

Usage:

    import asyncio
    from src.agents.courseware_flash_slideplan import run_courseware_flash_slideplan

    result = asyncio.run(run_courseware_flash_slideplan(
        instruction="材料力学第二章:轴向拉伸与压缩",
        material_path="uploads/第二章 拉伸、压缩1.pptx",
        audience="大二自动化",
    ))

    print(result["slide_plan_path"])
    # -> .../ChaoXingAgentWorkspace/projects/20260515_104233_a1b2c3d4/slide_plan.json

Returned dict shape:
    {
        "status": "success",
        "project_dir": str,
        "slide_plan_path": str,
        "material_markdown_path": str | None,
        "images_manifest_path": str | None,
        "agent_response": str,
        "log_file": str | None,
    }
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from src.agents._courseware_runtime import (
    AUTO_CONVERT_SCRIPT,
    CLAUDE_SDK_ROOT,
    SLIDE_PLAN_SCHEMA_PATH,
    get_courseware_logger,
    load_courseware_env,
)
from src.utils.paths import paths

# Default artifact root, matching src/claude_agents/courseware_flash.py so
# both the chatbot-style runner and this L3 entry write under the same
# top-level workspace.
DEFAULT_WORKSPACE = paths.workspace_dir


def _generate_project_dir(workspace_root: Path) -> Path:
    """Generate ``<workspace_root>/projects/<timestamp>_<uuid8>``."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_name = f"{timestamp}_{uuid.uuid4().hex[:8]}"
    return workspace_root / "projects" / project_name


async def run_courseware_flash_slideplan(
    instruction: str,
    material_path: Optional[str | Path] = None,
    project_dir: Optional[str | Path] = None,
    workspace_root: Optional[str | Path] = None,
    audience: str = "",
    log_file: Optional[str] = None,
    env_path: Optional[str] = None,
    provider: str = "xfyun",
    timeout: float = 600.0,
) -> dict[str, Any]:
    """Run Phase A + Phase B and return artifact paths.

    Args:
        instruction: Free-form teaching instruction from the user. Required.
        material_path: Optional path to PDF/PPTX/DOCX/etc. If absent, Phase A
            is skipped and the agent works from ``instruction`` only.
        project_dir: Directory that will hold ``sources/``, ``images/``,
            ``slide_plan.json``, and the agent log. If omitted, a timestamped
            subdirectory is generated under ``workspace_root``.
        workspace_root: Root for auto-generated project directories. Only
            used when ``project_dir`` is None. Defaults to
            :attr:`src.utils.paths.RuntimePaths.workspace_dir`.
        audience: Optional target audience string (e.g. ``"大二自动化"``).
        log_file: Optional file path for the structured logger.
        env_path: Optional .env override; defaults to ``<PROJECT_ROOT>/.env``.
        provider: AgentFactory provider key (default ``"xfyun"``).
        timeout: Per-attempt agent ask timeout in seconds.

    Returns:
        A dict with status / project_dir / slide_plan_path and side
        artifact paths. See module docstring for the exact shape.

    Raises:
        FileNotFoundError: ``material_path`` was given but does not exist.
        RuntimeError: source conversion failed, or the agent did not
            actually produce ``slide_plan.json``.
    """
    # Local imports keep module import cheap and avoid circulars.
    from claude_sdk.infra.agent_factory import AgentFactory  # noqa: WPS433

    # Load .env so AgentFactory can resolve provider credentials.
    load_courseware_env(env_path)

    logger = get_courseware_logger("chaoxing.courseware_flash_slideplan", log_file=log_file)
    runtime_log_path = getattr(logger, "runtime_log_path", None)
    logger.info("Starting courseware_flash slideplan pipeline")

    # Resolve project directory. If the caller did not specify one, mint
    # a `<workspace_root>/projects/<timestamp>_<uuid8>` directory so the
    # artifact layout matches src/claude_agents/courseware_flash.py.
    if project_dir is not None:
        project_path = Path(project_dir).resolve()
    else:
        workspace = Path(workspace_root).resolve() if workspace_root else DEFAULT_WORKSPACE
        project_path = _generate_project_dir(workspace).resolve()
    project_path.mkdir(parents=True, exist_ok=True)
    logger.info("Project directory: %s", project_path)

    # ---------- Phase A: source -> markdown + image manifest ----------
    material_md_path: Optional[Path] = None
    images_manifest_path: Optional[Path] = None

    if material_path is not None:
        material = Path(material_path).resolve()
        if not material.exists():
            raise FileNotFoundError(f"Material not found: {material}")
        if not AUTO_CONVERT_SCRIPT.exists():
            raise RuntimeError(f"auto_source_convert.py not found at {AUTO_CONVERT_SCRIPT}")

        logger.info("Phase A: converting %s", material)
        material_md_path, images_manifest_path = await _run_source_conversion(
            material=material,
            project_path=project_path,
            logger=logger,
        )
        if material_md_path:
            logger.info("Phase A markdown: %s", material_md_path)
        if images_manifest_path:
            logger.info("Phase A manifest: %s", images_manifest_path)
    else:
        logger.info("Phase A skipped (no material_path provided)")

    # ---------- Phase B: agent -> slide_plan.json ----------
    logger.info("Phase B: launching courseware_flash agent")

    agent = AgentFactory.create_agent(
        agent_name="courseware_flash",
        skills=["courseware_flash"],
        cwd=str(project_path),
        workspace=str(project_path),
        project_root=str(CLAUDE_SDK_ROOT),
        provider=provider,
        tools=["Read", "Write", "Glob"],
        permission_mode="acceptEdits",
    )

    slide_plan_path = project_path / "slide_plan.json"
    prompt = _build_slideplan_prompt(
        instruction=instruction,
        audience=audience,
        project_path=project_path,
        slide_plan_path=slide_plan_path,
        material_md_path=material_md_path,
        images_manifest_path=images_manifest_path,
    )

    await agent.start()
    try:
        agent_response = await agent.ask_with_retry(prompt, timeout=timeout)

        if not slide_plan_path.exists():
            raise RuntimeError(
                f"Agent did not produce slide_plan.json at {slide_plan_path}. "
                f"Agent response: {agent_response[:500]}"
            )

        # Validate JSON; if invalid, ask the agent to repair the exact byte
        # range and retry. LLMs occasionally drop unescaped `"` inside
        # Chinese strings, which the prompt warns about but cannot fully
        # prevent. Up to `max_repair_attempts` repair rounds.
        max_repair_attempts = 2
        last_decode_error: Optional[json.JSONDecodeError] = None
        for attempt in range(max_repair_attempts + 1):
            raw_text = slide_plan_path.read_text(encoding="utf-8")
            try:
                slide_plan_data = json.loads(raw_text)
                normalized_data, changed = _normalize_slide_plan(slide_plan_data)
                if changed:
                    slide_plan_path.write_text(
                        json.dumps(normalized_data, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    logger.info("Normalized slide_plan.json to fit downstream schema limits")
                last_decode_error = None
                break
            except json.JSONDecodeError as exc:
                last_decode_error = exc
                logger.warning(
                    "slide_plan.json invalid (attempt %d/%d): %s at line %d col %d",
                    attempt + 1,
                    max_repair_attempts + 1,
                    exc.msg,
                    exc.lineno,
                    exc.colno,
                )
                if attempt >= max_repair_attempts:
                    break
                repair_prompt = _build_repair_prompt(
                    slide_plan_path=slide_plan_path,
                    raw_text=raw_text,
                    error=exc,
                )
                agent_response = await agent.ask_with_retry(repair_prompt, timeout=timeout)

        if last_decode_error is not None:
            raise RuntimeError(
                f"slide_plan.json at {slide_plan_path} is not valid JSON after "
                f"{max_repair_attempts + 1} attempts: {last_decode_error.msg} "
                f"at line {last_decode_error.lineno} col {last_decode_error.colno}. "
                f"Agent response: {agent_response[:500]}"
            )
    finally:
        await agent.close()

    logger.info("slide_plan.json written: %s", slide_plan_path)

    return {
        "status": "success",
        "project_dir": str(project_path),
        "slide_plan_path": str(slide_plan_path),
        "material_markdown_path": str(material_md_path) if material_md_path else None,
        "images_manifest_path": str(images_manifest_path) if images_manifest_path else None,
        "agent_response": agent_response,
        "log_file": runtime_log_path,
    }


async def _run_source_conversion(
    material: Path,
    project_path: Path,
    logger,
) -> tuple[Optional[Path], Optional[Path]]:
    """Invoke auto_source_convert.py and locate the resulting artifacts."""
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        str(AUTO_CONVERT_SCRIPT),
        str(material),
        str(project_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_b, stderr_b = await process.communicate()
    stdout = stdout_b.decode("utf-8", errors="replace") if stdout_b else ""
    stderr = stderr_b.decode("utf-8", errors="replace") if stderr_b else ""

    if process.returncode != 0:
        logger.error("auto_source_convert failed (rc=%s): %s", process.returncode, stderr)
        raise RuntimeError(f"auto_source_convert failed (rc={process.returncode}): {stderr}")

    if stdout:
        logger.info("auto_source_convert stdout:\n%s", stdout)
    if stderr:
        logger.debug("auto_source_convert stderr:\n%s", stderr)

    md_path: Optional[Path] = None
    sources_dir = project_path / "sources"
    if sources_dir.exists():
        preferred = sources_dir / f"{material.stem}.md"
        if preferred.exists():
            md_path = preferred
        else:
            md_candidates = sorted(sources_dir.glob("*.md"))
            if md_candidates:
                md_path = md_candidates[0]

    manifest_path: Optional[Path] = None
    manifest = project_path / "images" / "manifest.json"
    if manifest.exists():
        manifest_path = manifest

    return md_path, manifest_path


def _build_slideplan_prompt(
    instruction: str,
    audience: str,
    project_path: Path,
    slide_plan_path: Path,
    material_md_path: Optional[Path],
    images_manifest_path: Optional[Path],
) -> str:
    """Compose the per-call prompt for the courseware_flash agent.

    System prompt (from prompts/courseware_flash.yaml + skills/courseware_flash.yaml)
    already specifies the content_blocks schema and authoring rules. This
    prompt only supplies per-task context: instruction, paths, and the
    explicit constraint that the agent must only produce slide_plan.json.
    """
    parts: list[str] = [
        "你的本次任务:仅生成 slide_plan.json,**不要**执行渲染、导出、讲稿生成等下游步骤。",
        "",
        f"用户需求:{instruction}",
    ]
    if audience:
        parts.append(f"目标受众:{audience}")

    parts.extend(
        [
            f"项目目录:{project_path}",
            f"slide_plan.json 输出路径:{slide_plan_path}",
        ]
    )

    if material_md_path is not None:
        parts.extend(
            [
                "",
                f"源文档(已转 markdown):{material_md_path}",
                "请先 Read 该 markdown,提取章节结构、关键公式、例题、定义后再排版。",
            ]
        )
    else:
        parts.append("本次没有源文档,基于 instruction 自行组织教学内容。")

    if images_manifest_path is not None:
        parts.extend(
            [
                "",
                f"图片清单:{images_manifest_path}",
                "如需插图,先 Read 该 manifest.json,只可引用其中的 filename 字段。",
                'image block 的 source_type 固定为 "path",source 必须等于 manifest 中某个 filename。',
                "If the manifest contains same-page or semantically matched teaching figures, prefer using image blocks on 1-2 concept_explanation slides.",
                "Do not leave the whole deck with zero image blocks when the manifest clearly contains relevant teaching figures.",
            ]
        )
    else:
        parts.append("本次没有 manifest.json,**禁止**在任何 slide 中加入 image block。")

    parts.extend(
        [
            "",
            "硬约束:",
            "- 严格遵守 system prompt 中的 content_blocks 规范。",
            "- 总页数 10-20,每个 concept_explanation 至少含一个非 bullets 块。",
            "- teaching_goal 必须是可验证的一句话学习成果。",
            "- 直接用 Write 工具落盘到 slide_plan.json,**不要**把 JSON 输出在回答里。",
            '- **JSON 字符串值内禁止出现未转义的英文双引号 `"`**;中文里要引用术语请用 「」/『』/《》/中文引号 替代,否则 JSON 解析会直接报错。',
            "- 完成后只回一句:已完成。",
        ]
    )

    return "\n".join(parts)


def _build_repair_prompt(
    slide_plan_path: Path,
    raw_text: str,
    error: json.JSONDecodeError,
) -> str:
    """Compose a repair instruction telling the agent how to fix one
    JSON syntax error in slide_plan.json.

    The agent is asked to use Read + Edit to fix ONLY the offending
    substring (typically an unescaped double quote inside a Chinese
    string value). It must NOT regenerate the file from scratch.
    """
    lines = raw_text.split("\n")
    lineno = max(1, min(error.lineno, len(lines)))
    line_text = lines[lineno - 1] if lines else ""
    # Show 2 lines before / after for context.
    start = max(0, lineno - 3)
    end = min(len(lines), lineno + 2)
    excerpt_lines = []
    for i in range(start, end):
        marker = ">>" if (i + 1) == lineno else "  "
        excerpt_lines.append(f"{marker} {i + 1:>5}: {lines[i]}")
    excerpt = "\n".join(excerpt_lines)

    parts = [
        f"刚才生成的 {slide_plan_path.name} 不是合法的 JSON。",
        f"解析错误:{error.msg}",
        f"位置:line {error.lineno} col {error.colno} (char {error.pos})",
        "",
        "出错附近的内容(>> 是出错的行):",
        excerpt,
        "",
        "出错行原文(供精确匹配):",
        line_text,
        "",
        "请按下列步骤修复,**只**改坏掉的那个字符串,不要重新生成整个文件:",
        f"1. 用 Read 工具读取 {slide_plan_path}。",
        '2. 用 Edit 工具修改出错的那一行/那一段。常见原因是字符串值里出现了未转义的英文双引号 `"`。',
        '3. 把中文里用来引用术语的英文 `""` 替换成 「」、『』、《》、中文引号或显式转义 `\\"`。',
        "4. 不要改动其他 slide 的内容,不要改字段名,不要改结构。",
        "5. 改完后用 Read 工具再读一次,确认整个文件能被 json.loads 解析。",
        "6. 完成后只回一句:已修复。",
    ]
    return "\n".join(parts)


def _load_slide_plan_schema() -> dict[str, Any]:
    """Load slide_plan schema used by downstream validation."""
    if not SLIDE_PLAN_SCHEMA_PATH.exists():
        return {}
    return json.loads(SLIDE_PLAN_SCHEMA_PATH.read_text(encoding="utf-8"))


def _extract_bullets_limit(schema: dict[str, Any]) -> int:
    """Extract global bullets maxItems from schema with a safe fallback."""
    try:
        return int(schema["properties"]["slides"]["items"]["properties"]["bullets"]["maxItems"])
    except (KeyError, TypeError, ValueError):
        return 4


def _normalize_slide_plan(slide_plan: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Clamp known schema-sensitive fields after agent generation."""
    bullets_limit = _extract_bullets_limit(_load_slide_plan_schema())
    changed = False

    for slide in slide_plan.get("slides", []):
        bullets = slide.get("bullets")
        if (
            slide.get("type") == "summary_slide"
            and isinstance(bullets, list)
            and len(bullets) > bullets_limit
        ):
            slide["bullets"] = bullets[:bullets_limit]
            changed = True

    return slide_plan, changed
