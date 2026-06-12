# ChaoXingAgent Flow

## Main Flow

1. Teacher uploads lesson assets and workflow metadata.
2. `src/workflows/teacher_workflow.py` normalizes the request and invokes the parser stages.
3. `src/pipelines/file_parser_pipeline.py` converts assets into normalized units, sections, pages, and `StructuredLessonContent`.
4. `src/pipelines/generate_pipeline.py` turns structured lesson data into `presentation_outline`, `lesson_script`, and `ppt_outline`.
5. The workflow optionally renders a PPTX and writes a workflow artifact JSON.
6. Student-side calls package a `StudentAgentRequest` from teacher artifacts plus session/progress/history state.
7. `src/agents/student/agent.py` runs QA and decision stages, maps references to knowledge-point matches, and returns `StudentAgentResponse`.
8. Memory and frontend/backend consumers persist `qa_record` and advance session/progress for the next turn.

## Branch Flows

- If no LLM callable is provided in generation, the generate pipeline falls back to deterministic outline generation.
- If rendering fails, teacher workflow still returns success with `render_error` metadata.
- If student matching cannot locate a precise page or section, orchestration falls back to current context and lesson-level knowledge points.
- If optional lesson script, session, or progress are absent, student request normalization backfills from the remaining available state.

## Data Entry Points

- CLI entry point: `src/main.py`
- Teacher workflow request payloads
- Student agent request payloads
- Local asset files loaded by `src/utils/file_loader.py`
- Environment variables for provider, model, API key, base URL, timeout, and rate limits

## Processing Chain

- Asset files -> document units -> parsed document -> `StructuredLessonContent`
- `StructuredLessonContent` + teacher notes -> outline/script/deck artifacts
- `StructuredLessonContent` + lesson script + session context + question -> QA/decision outputs -> `StudentAgentResponse`
- `StudentAgentResponse` -> session/progress updates + QA persistence

## Output Points

- JSON output files written by the CLI and workflow helpers
- Optional PPTX rendering output
- Student response payload for application consumption
- Memory store updates under the student path

## External Dependencies

- OpenAI-compatible chat-completions API accessed by `src/utils/llm_client.py`
- Configured provider defaults to DeepSeek unless overridden
- Windows runtime support for Office-related parsing helpers via `pywin32`
- Local filesystem for artifact logs, test fixtures, and generated outputs
