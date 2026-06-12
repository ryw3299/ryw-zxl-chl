#!/usr/bin/env python3
"""
validate_slide_plan.py — Validate slide_plan.json against JSON Schema

Usage:
    python validate_slide_plan.py <project_path>
    python validate_slide_plan.py <slide_plan.json>
"""

import json
import os
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:
    print("ERROR: jsonschema is required. Install: pip install jsonschema")
    sys.exit(1)


def resolve_skill_dir() -> Path:
    script = Path(__file__).resolve()
    return script.parent.parent


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main(target: str) -> int:
    target_path = Path(target).resolve()

    if target_path.is_dir():
        plan_path = target_path / "slide_plan.json"
    else:
        plan_path = target_path

    if not plan_path.exists():
        print(f"ERROR: slide_plan.json not found at {plan_path}")
        return 1

    skill_dir = resolve_skill_dir()
    schema_path = skill_dir / "templates" / "slide_plan_schema.json"
    if not schema_path.exists():
        print(f"ERROR: Schema not found at {schema_path}")
        return 1

    plan = load_json(plan_path)
    schema = load_json(schema_path)

    validator = jsonschema.Draft7Validator(schema)
    errors = sorted(validator.iter_errors(plan), key=lambda e: e.path)

    if not errors:
        slide_count = plan.get("slide_count", 0)
        actual = len(plan.get("slides", []))
        if slide_count != actual:
            print(f"WARNING: slide_count ({slide_count}) != actual slides ({actual})")
            return 1
        print("OK: slide_plan.json is valid.")
        return 0

    print(f"FAILED: {len(errors)} validation error(s):\n")
    for err in errors:
        path = "/".join(str(p) for p in err.path) if err.path else "root"
        print(f"  [{path}] {err.message}")
    return 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <project_path|slide_plan.json>")
        sys.exit(1)
    sys.exit(main(sys.argv[1]))
