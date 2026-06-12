#!/usr/bin/env python3
"""
generate_spec_lock.py — Render spec_lock.md from slide_plan + template

Usage:
    python generate_spec_lock.py <project_path>
"""

import json
import sys
from pathlib import Path

try:
    import jinja2
except ImportError:
    print("ERROR: jinja2 is required. Install: pip install jinja2")
    sys.exit(1)


def resolve_skill_dir() -> Path:
    script = Path(__file__).resolve()
    return script.parent.parent


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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
    tmpl_path = skill_dir / "templates" / "spec_lock.template.md"

    slide_plan = load_json(plan_path)
    global_style = load_json(style_path)

    if slide_plan.get("global_style"):
        for key, val in slide_plan["global_style"].items():
            if isinstance(val, dict) and isinstance(global_style.get(key), dict):
                global_style[key].update(val)
            else:
                global_style[key] = val

    ctx = {
        **global_style,
        "slides": slide_plan.get("slides", []),
    }

    with open(tmpl_path, "r", encoding="utf-8") as f:
        raw = f.read()
    template = jinja2.Template(raw)
    rendered = template.render(**ctx)

    out_path = proj / "spec_lock.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(rendered)
    print(f"  wrote {out_path.relative_to(proj)}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <project_path>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
