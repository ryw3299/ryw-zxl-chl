#!/usr/bin/env python3
"""
generate_notes.py — Generate minimal notes/total.md from slide_plan.json

Each page gets exactly one sentence (teaching_goal or title fallback).
This satisfies total_md_split.py which requires notes/total.md to exist.

Usage:
    python generate_notes.py <project_path>
"""

import json
import sys
from pathlib import Path


def main(project_path: str) -> int:
    proj = Path(project_path).resolve()
    if not proj.is_dir():
        print(f"ERROR: Project path does not exist: {proj}")
        return 1

    plan_path = proj / "slide_plan.json"
    if not plan_path.exists():
        print(f"ERROR: slide_plan.json not found in {proj}")
        return 1

    with open(plan_path, "r", encoding="utf-8") as f:
        plan = json.load(f)

    slides = plan.get("slides", [])
    deck_title = plan.get("deck_title", "Courseware")

    lines = [f"# {deck_title}\n"]
    for slide in slides:
        goal = slide.get("teaching_goal") or slide.get("title", "")
        lines.append(f"\n# {slide['slide_id']:02d} {slide['slug'].replace('_', ' ')}\n")
        lines.append(f"{goal}\n")

    notes_dir = proj / "notes"
    notes_dir.mkdir(parents=True, exist_ok=True)
    out_path = notes_dir / "total.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("".join(lines))

    print(f"  wrote {out_path.relative_to(proj)} ({len(slides)} page(s))")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <project_path>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
