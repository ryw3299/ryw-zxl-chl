---
name: courseware-flash
description: >
  Fast lane for teacher courseware generation. LLM produces slide_plan.json;
  Python renderer generates SVGs from fixed Jinja2 templates and reuses the
  existing ppt-master export pipeline. Use when user asks for "课件",
  "教案", "讲课PPT", "课程", "教学", "课堂", "courseware", "teaching slides",
  "lecture notes", or explicitly mentions "courseware-flash".
---

# Courseware Flash Skill

> Fast lane for teacher courseware generation. Zero design drift, deterministic output.

**Core Pipeline**: `Teaching Topic (+ Source) → slide_plan.json → render_from_plan.py → svg_output/*.svg → svg_quality_checker.py → total_md_split.py → finalize_svg.py → svg_to_pptx.py → editable PPTX`

## When to Use

Use **courseware-flash** instead of `ppt-master/SKILL.md` when:
- The user explicitly says "课件", "教案", "讲课", "课程", "教学", "课堂", "courseware", "teaching slides", "lecture", or "lesson".
- The user explicitly mentions `courseware-flash`.

Use **ppt-master/SKILL.md** for general business presentations, data briefings, reports, or when the user wants full multi-role design freedom.

## Execution Discipline

1. **SERIAL EXECUTION** — Steps run in order; output of each step feeds the next.
2. **NO SPECULATIVE EXECUTION** — Do not pre-write SVGs while still planning slide structure.
3. **SLIDE_PLAN IS THE CONTRACT** — All content lives in `slide_plan.json`. If the user asks to change content, edit `slide_plan.json` and re-run `render_from_plan.py`.
4. **REUSE EXISTING ENGINE** — `svg_quality_checker.py`, `total_md_split.py`, `finalize_svg.py`, `svg_to_pptx.py` are used as black boxes. Do NOT modify them.

---

## Pre-phase: Source Material Processing (Optional)

If the user provides source files (PDF / PPTX / DOCX / XLSX / URL / Markdown / text), convert them first. If the user provides **only** a topic description, skip this phase and use conversation content directly.

**Quick way (auto-detect file type):**

```bash
python skills/courseware-flash/scripts/auto_source_convert.py <source_file> <project_path>
```

**Manual way (when auto-detect fails or you need fine-grained control):**

| Source Type | Command |
|-------------|---------|
| PDF | `python3 skills/ppt-master/scripts/source_to_md/pdf_to_md.py <file> -o <project>/sources/<name>.md` |
| PPTX / PowerPoint | `python3 skills/ppt-master/scripts/source_to_md/ppt_to_md.py <file> -o <project>/sources/<name>.md` |
| DOCX / Word / ODT / RTF / EPUB | `python3 skills/ppt-master/scripts/source_to_md/doc_to_md.py <file> -o <project>/sources/<name>.md` |
| XLSX / Excel | `python3 skills/ppt-master/scripts/source_to_md/excel_to_md.py <file> -o <project>/sources/<name>.md` |
| Web URL | `python3 skills/ppt-master/scripts/source_to_md/web_to_md.py <URL> -o <project>/sources/<name>.md` |
| Markdown / TXT | Copy directly to `<project>/sources/` |

After conversion, **read the generated Markdown** to extract the table of contents, key concepts, examples, and formulas. Use these as the factual basis for slide_plan.json generation.

---

## Phase A: Planning (LLM)

### Step 0 — Project Setup

Create the project directory:

```bash
mkdir -p projects/<project_name>
```

Project naming: use a short ASCII slug derived from the course title, e.g. `mechanics_ch2`, `control_ch1`, `english_unit3`.

If source conversion was performed in Pre-phase, the `sources/` subdirectory already exists inside the project.

### Step 1 — Understand teaching intent

Gather from the user (or infer from request + source content):
- Course title
- Target audience (e.g., "大二自动化")
- Number of slides (recommend 10–20 for a single lesson)
- Key topics / sections
- Any specific examples or cases to include

> **When source markdown is available:** Read the converted markdown and extract:
> - Chapter / section structure
> - Key definitions, formulas, and theorems
> - Examples and case studies
> - Diagram descriptions
> Use these extracted elements to inform slide selection and bullet content. Do NOT invent content that contradicts the source.

### Step 2 — Write slide_plan.json

Produce `<project_path>/slide_plan.json` conforming to the schema in `skills/courseware-flash/templates/slide_plan_schema.json`.

**Allowed slide types** (Phase 1):
- `title_slide` — course cover
- `chapter_transition` — chapter divider with topic preview
- `lesson_objectives` — learning goals (≤4 bullets)
- `concept_explanation` — core knowledge with bullets + optional teaching tip
- `comparison` — side-by-side comparison of two concepts
- `classroom_question` — interactive prompt + discussion points
- `summary_slide` — wrap-up with numbered takeaways

**Field rules**:
- `filename` MUST be `{NN}_{slug}.svg` (e.g. `01_title_slide.svg`).
- `bullets` array ≤ 4 items. Each item has `text` (required) and optional `sub`.
- `teaching_goal` is a one-sentence note used for `notes/total.md`.
- `rhythm` is one of `anchor`, `dense`, `breathing`.

### Step 3 — Validate slide_plan.json

Run:
```bash
python skills/courseware-flash/scripts/validate_slide_plan.py <project_path>
```
Fix any schema errors before proceeding.

---

## Phase B: Rendering & Export (Scripts)

### Step 4 — Generate SVGs + notes

Run:
```bash
python skills/courseware-flash/scripts/render_from_plan.py <project_path>
```

This writes:
- `<project_path>/svg_output/*.svg`
- `<project_path>/notes/total.md`

### Step 5 — Quality check

Run:
```bash
python skills/ppt-master/scripts/svg_quality_checker.py <project_path>
```

Fix any reported issues (usually means fixing `slide_plan.json` and re-running Step 4).

### Step 6 — Post-processing pipeline

Run sequentially, one command at a time:
```bash
python skills/ppt-master/scripts/total_md_split.py <project_path>
python skills/ppt-master/scripts/finalize_svg.py <project_path>
python skills/ppt-master/scripts/svg_to_pptx.py <project_path>
```

The final PPTX is written to `<project_path>/output/`.

---

## Quick Start: One-Shot Agent Execution

For a fully automated run where the user provides only a topic and optionally a source file, execute the following steps in one continuous pass without BLOCKING confirmations:

```
1. (Optional) auto_source_convert.py  →  sources/<name>.md
2. Read sources/<name>.md (if exists) + user's instruction
3. Generate slide_plan.json
4. validate_slide_plan.py
5. render_from_plan.py
6. svg_quality_checker.py
7. total_md_split.py → finalize_svg.py → svg_to_pptx.py
```

No user confirmation gates exist in courseware-flash. The only reason to pause is if `validate_slide_plan.py` or `svg_quality_checker.py` reports errors that need fixing.

---

## Optional: spec_lock.md

If you want the quality checker to perform drift detection, generate `spec_lock.md`:
```bash
python skills/courseware-flash/scripts/generate_spec_lock.py <project_path>
```

This is optional; `svg_quality_checker.py` skips drift checks when `spec_lock.md` is absent.

## Visual Edit Loop

If the user asks to tweak a slide after export ("改一下第3页", "调字号", etc.):
1. Identify which slide in `slide_plan.json` needs change.
2. Edit `slide_plan.json`.
3. Re-run **Step 4 → Step 5 → Step 6**.

Do NOT hand-edit SVGs for content changes; always go through `slide_plan.json` so the source of truth stays clean.

## Architecture

- `skills/courseware-flash/SKILL.md` — this file.
- `skills/courseware-flash/templates/global_style.json` — fixed teaching blue/white style tokens.
- `skills/courseware-flash/templates/slide_plan_schema.json` — JSON Schema for validation.
- `skills/courseware-flash/templates/svgj2/*.svg.j2` — Jinja2 SVG templates (one per slide type).
- `skills/courseware-flash/scripts/render_from_plan.py` — main renderer.
- `skills/courseware-flash/scripts/validate_slide_plan.py` — schema validator.
- `skills/courseware-flash/scripts/generate_spec_lock.py` — optional spec_lock renderer.
- `skills/courseware-flash/scripts/generate_notes.py` — standalone notes generator (also embedded in render_from_plan.py).
- `skills/courseware-flash/scripts/auto_source_convert.py` — automatic source file type detection & conversion.
