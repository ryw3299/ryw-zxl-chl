# ChaoXingAgent Project Brief

## Project Goal

Build a teaching-content pipeline that turns uploaded lesson assets into structured course artifacts for teachers, and extend those artifacts into a student-facing question answering flow.

## Inputs

- Teacher lesson assets such as `ppt`, `pptx`, `pdf`, `docx`, and `txt`
- Teacher workflow instructions and notes
- Student question turns plus lesson artifacts, session state, progress, and QA history
- Runtime LLM configuration from environment variables

## Outputs

- Teacher-side `structured_content`, `presentation_outline`, `lesson_script`, and `ppt_outline`
- Optional rendered PPTX and workflow artifact JSON
- Student-side `StudentAgentResponse`, updated session/progress snapshots, and persistable `QARecord`

## Primary Users

- Internal developers integrating teacher and student workflows
- Teacher-side product flows that need standardized lesson artifacts
- Student-side product flows that need grounded QA over teacher-generated lesson content

## Success Criteria

- Teacher workflow runs end to end from asset parsing to artifact generation
- Student workflow consumes teacher artifacts without redefining their shape
- Contracts remain stable enough for parallel implementation
- Retrieval, memory, skills, and orchestration are split cleanly enough for independent workers
- Tests cover contract integrity and core path behavior

## Non-Goals

- Do not redesign the teacher workflow around raw PPT assets again
- Do not couple student orchestration directly to storage or retrieval internals
- Do not let each module invent its own response schema
- Do not optimize for production-scale distributed deployment in this phase
