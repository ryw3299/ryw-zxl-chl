# ChaoXingAgent Contract

## Core System Contract

The system is split into two artifact layers:

- Teacher layer produces stable lesson artifacts from uploaded source files.
- Student layer consumes those artifacts and must not redefine their structure.

## Key Inputs And Outputs

### Teacher Side

- Input request: course metadata, lesson identifiers, source assets, parse instruction, teacher notes, generation instruction
- Output artifacts:
  - `StructuredLessonContent`
  - `PresentationOutline`
  - `LessonScript`
  - `PPTOutline`
  - optional rendered PPTX

### Student Side

- Input request: `StudentAgentRequest`
- Output response: `StudentAgentResponse`
- Persistence outputs:
  - `LearningSession`
  - `LearningProgress`
  - `QARecord`

## Frozen Schemas

The critical student contract lives in `src/schemas/student_schemas.py` and related common schemas.

Freeze:

- `StudentAgentRequest`
- `StudentAgentResponse`
- `KnowledgePointMatch`
- `RetrievedContextItem`
- `LearningSession`
- `LearningProgress`
- `QAHistoryItem`
- `QARecord`

## Frozen Enums And Allowed Values

- `StudentQuestionType`:
  - `definition`
  - `reasoning`
  - `procedure`
  - `example`
  - `comparison`
  - `summary`
  - `unknown`
- `UnderstandingLevel`:
  - `full`
  - `partial`
  - `none`
- `NextAction`:
  - `resume`
  - `supplement_then_resume`
  - `reteach_slowly`
  - `trigger_game`
- `RetrievedContextItem.source`:
  - `page`
  - `section`
  - `script_block`

## Error Conventions

- Invalid teacher workflow requests raise `ValueError` before pipeline execution.
- Missing LLM configuration raises `LLMConfigurationError`.
- HTTP and transport failures for model calls raise `LLMRequestError`.
- Student schema mismatches fail during Pydantic validation and must not be silently ignored.

## Boundary Conditions

- `structured_content.lesson_id` must match `StudentAgentRequest.lesson_id`.
- `lesson_script.metadata.lesson_id`, when present, must match the request lesson.
- Session and progress snapshots must match both `lesson_id` and `session_id`.
- Student orchestration may infer missing `course_id`, `current_section_id`, `current_page`, and `current_script_block_id` from session/progress, but must not fabricate unrelated lesson identities.
- Generation may fall back to deterministic section/card construction, but output schemas must still validate.

## Key Cases

- Teacher path with no render support still returns a usable artifact bundle.
- Student path with sparse context still returns a schema-valid response and a persistable record.
- Retrieval output must be convertible to `RetrievedContextItem`.
- Memory and retrieval modules must remain replaceable without changing the external student response contract.
