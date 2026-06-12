#!/usr/bin/env python3
"""
render_from_plan.py — Courseware Flash SVG renderer

Reads <project>/slide_plan.json and renders SVGs into <project>/svg_output/
using Jinja2 templates from skills/courseware-flash/templates/svgj2/.

Also generates a minimal <project>/notes/total.md so total_md_split.py
has something to split during post-processing.

Usage:
    python render_from_plan.py <project_path>
"""

import json
import os
import sys
from pathlib import Path

try:
    import jinja2
except ImportError:
    print("ERROR: jinja2 is required. Install: pip install jinja2")
    sys.exit(1)


def resolve_skill_dir() -> Path:
    """Return the courseware-flash skill directory."""
    script = Path(__file__).resolve()
    return script.parent.parent


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_context(global_style: dict, slide_plan: dict) -> dict:
    """Merge global_style with deck-level metadata for template rendering."""
    ctx = {}
    ctx.update(global_style)
    ctx["deck_title"] = slide_plan.get("deck_title", "")
    ctx["audience"] = slide_plan.get("audience", "")
    ctx["language"] = slide_plan.get("language", "zh")
    ctx["slide_count"] = slide_plan.get("slide_count", 0)
    return ctx


def make_template_env(templates_dir: Path) -> "jinja2.Environment":
    """Create a Jinja environment that safely escapes SVG/XML text values."""
    return jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(templates_dir)),
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def _normalize_bullet_item(item) -> dict:
    if isinstance(item, str):
        return {"text": item}
    if isinstance(item, dict):
        text = item.get("text") or item.get("title") or ""
        sub = item.get("sub") or item.get("detail") or item.get("meaning")
        return {"text": text, "sub": sub}
    return {"text": str(item)}


def _where_to_sub(where_items: list) -> str:
    parts = []
    for item in where_items or []:
        if not isinstance(item, dict):
            continue
        symbol = item.get("symbol")
        meaning = item.get("meaning")
        if symbol and meaning:
            parts.append(f"{symbol}: {meaning}")
    return "；".join(parts)


def normalize_slide(slide: dict) -> dict:
    """Flatten structured slide_plan fields into template-friendly keys."""
    normalized = dict(slide)
    slide_type = normalized.get("type")

    if slide_type == "lesson_objectives":
        normalized["bullets"] = [{"text": item} for item in normalized.get("objectives", [])]
        return normalized

    if slide_type == "chapter_transition":
        normalized["bullets"] = [{"text": item} for item in normalized.get("preview_points", [])]
        return normalized

    if slide_type == "summary_slide":
        normalized["bullets"] = [{"text": item} for item in normalized.get("key_points", [])]
        return normalized

    if slide_type != "concept_explanation":
        return normalized

    bullets = []
    side_notes = []
    hook_text = None
    image_href = None
    image_caption = None

    for block in normalized.get("content_blocks", []):
        if not isinstance(block, dict):
            continue

        block_type = block.get("type")
        if block_type == "hook" and not hook_text:
            hook_text = block.get("text")
            continue

        if block_type == "image" and block.get("source_type") == "path" and block.get("source"):
            image_href = f"../images/{block['source']}"
            image_caption = block.get("caption")
            continue

        if block_type == "bullets":
            bullets.extend(_normalize_bullet_item(item) for item in block.get("items", []))
            continue

        if block_type == "steps":
            bullets.extend(_normalize_bullet_item(item) for item in block.get("items", []))
            continue

        if block_type == "formula":
            sub = block.get("latex")
            where_sub = _where_to_sub(block.get("where", []))
            if where_sub:
                sub = f"{sub}；{where_sub}" if sub else where_sub
            bullets.append(
                {
                    "text": block.get("caption") or block.get("title") or "公式",
                    "sub": sub,
                }
            )
            continue

        if block_type == "example":
            lines = [part for part in [block.get("given"), block.get("solve"), block.get("result")] if part]
            bullets.append(
                {
                    "text": block.get("title") or "示例",
                    "sub": "；".join(lines) if lines else None,
                }
            )
            continue

        if block_type in {"pitfall", "analogy"}:
            label = "易错点" if block_type == "pitfall" else (block.get("title") or "类比")
            side_notes.append({"label": label, "text": block.get("text") or ""})

    normalized["bullets"] = bullets[:6]
    normalized["hook_text"] = hook_text
    normalized["side_notes"] = side_notes[:2]
    normalized["image_href"] = image_href
    normalized["image_caption"] = image_caption
    return normalized


def render_slide(template_env, slide: dict, base_ctx: dict) -> str:
    """Render a single slide SVG string."""
    tmpl_name = f"{slide['type']}.svg.j2"
    try:
        template = template_env.get_template(tmpl_name)
    except jinja2.TemplateNotFound:
        raise RuntimeError(
            f"Template not found for slide type '{slide['type']}': {tmpl_name}"
        )

    ctx = {**base_ctx, **normalize_slide(slide)}
    return template.render(**ctx)


def generate_total_md(slides: list, deck_title: str) -> str:
    """Generate minimal notes/total.md (1 sentence per page)."""
    lines = [f"# {deck_title}\n"]
    for slide in slides:
        goal = slide.get("teaching_goal") or slide.get("title", "")
        lines.append(f"\n# {slide['slide_id']:02d} {slide['slug'].replace('_', ' ')}\n")
        lines.append(f"{goal}\n")
    return "".join(lines)


def main(project_path: str) -> int:
    proj = Path(project_path).resolve()
    if not proj.is_dir():
        print(f"ERROR: Project path does not exist: {proj}")
        return 1

    plan_path = proj / "slide_plan.json"
    if not plan_path.exists():
        print(f"ERROR: slide_plan.json not found in {proj}")
        return 1

    skill_dir = resolve_skill_dir()
    style_path = skill_dir / "templates" / "global_style.json"
    templates_dir = skill_dir / "templates" / "svgj2"

    slide_plan = load_json(plan_path)
    global_style = load_json(style_path)

    # Merge optional per-project style overrides
    if slide_plan.get("global_style"):
        for key, val in slide_plan["global_style"].items():
            if isinstance(val, dict) and isinstance(global_style.get(key), dict):
                global_style[key].update(val)
            else:
                global_style[key] = val

    base_ctx = build_context(global_style, slide_plan)

    env = make_template_env(templates_dir)

    svg_out = proj / "svg_output"
    svg_out.mkdir(parents=True, exist_ok=True)

    slides = slide_plan.get("slides", [])
    if not slides:
        print("WARNING: No slides found in slide_plan.json")
        return 1

    for slide in slides:
        svg_text = render_slide(env, slide, base_ctx)
        out_path = svg_out / slide["filename"]
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(svg_text)
        print(f"  wrote {out_path.relative_to(proj)}")

    # Generate minimal notes/total.md
    notes_dir = proj / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    total_md = generate_total_md(slides, slide_plan.get("deck_title", "Courseware"))
    total_md_path = notes_dir / "total.md"
    with open(total_md_path, "w", encoding="utf-8") as f:
        f.write(total_md)
    print(f"  wrote {total_md_path.relative_to(proj)}")

    print(f"\nDone. {len(slides)} slide(s) rendered.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <project_path>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
