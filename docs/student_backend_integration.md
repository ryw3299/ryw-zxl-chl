# Student Agent Backend Integration

## Purpose

This document is for backend engineers who need to call the student agent from services or APIs.

Current student chain status:

- The student chain is already wired as an OpenHands-based agent.
- It supports grounded tool use through:
  - `search`
  - `retrieve`
  - `session`
  - `memory`
  - `game`
- It can run in two modes:
  - fallback mode: framework is active, but answer/decision fall back to local rules
  - real agent mode: answer and decision are both produced through the real LLM path

The formal integration target is:

- backend builds `StudentAgentRequest`
- backend builds a real `LLM` instance
- backend calls `run_student_agent(request, llm=llm)`
- backend consumes `StudentAgentResponse`

## Formal Entry Points

Use these public entry points:

- [`src\agents\student\__init__.py`](/src/agents/student/__init__.py)
- [`src\agents\student\agent.py`](/src/agents/student/agent.py)

Public functions:

- `build_student_agent_turn(request, llm=None) -> dict`
- `run_student_agent(request, llm=None) -> dict`

Backend should prefer:

- `run_student_agent(...)` for production path
- `build_student_agent_turn(...)` for debugging and observability

## Required Request Contract

The request schema is defined in:

- [`src\schemas\student_schemas.py`](/src/schemas/student_schemas.py)

Backend must provide a `StudentAgentRequest`.

Minimum practical fields:

- `lesson_id`
- `session_id`
- `question`
- one lesson-content source:
  - `turn_context` for the service-layer path
  - or `structured_content` for the legacy agent-driven path

Recommended fields:

- `course_id`
- `lesson_script`
- `session`
- `progress`
- `history_qa`
- `current_section_id`
- `current_page`
- `current_script_block_id`
- `student_profile`

Important constraint:

- `structured_content.lesson_id` must equal `request.lesson_id` when `structured_content` is present.
- `lesson_script.metadata.lesson_id` must equal `request.lesson_id` when that metadata value is present.
- `session` and `progress` must use the same `lesson_id` and `session_id` as the request.

## Required Response Contract

The response schema is also defined in:

- [`src\schemas\student_schemas.py`](/src/schemas/student_schemas.py)

Backend will receive a `StudentAgentResponse`-shaped dict.

Most important fields:

- `answer`
- `references`
- `question_type`
- `understanding_level`
- `recommended_narration_level`
- `next_action`
- `reason`
- `matched_knowledge_points`
- `matched_section_id`
- `matched_page`
- `matched_script_block_id`
- `target_section_id`
- `target_page`
- `target_script_block_id`
- `updated_session`
- `updated_progress`
- `qa_record`
- `metadata`

Backend typically uses them like this:

- UI rendering:
  - `answer`
  - `references`
  - `suggested_questions`
  - `metadata["game"]` when `next_action` is `trigger_game`
  - `recommended_narration_level` when the player can switch narration depth

- teaching flow / routing:
  - `next_action`
  - `reason`
  - `target_section_id`
  - `target_page`
  - `target_script_block_id`

- persistence / audit:
  - `updated_session`
  - `updated_progress`
  - `qa_record`
  - `metadata["tool_trace"]`

## Real LLM Configuration

Current `.env` convention:

- `LLM_PROVIDER`
- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`

Current project example:

- provider: `deepseek`
- model: `deepseek-chat`
- base URL: `https://api.deepseek.com`

For OpenHands/LiteLLM compatibility, the effective model string should be:

- `deepseek/deepseek-chat`

## Recommended Integration Code

```python
from pydantic import SecretStr
from openhands.sdk.llm import LLM

from src.agents.student import run_student_agent
from src.schemas import StudentAgentRequest


def build_student_llm() -> LLM:
    return LLM(
        model="deepseek/deepseek-chat",
        api_key=SecretStr("YOUR_LLM_API_KEY"),
        base_url="https://api.deepseek.com",
        litellm_extra_body={},
    )


def call_student_agent(request_payload: dict) -> dict:
    request = StudentAgentRequest.model_validate(request_payload)
    llm = build_student_llm()
    return run_student_agent(request, llm=llm)
```

## Debugging Integration Code

When backend needs full traceability, use:

```python
from pydantic import SecretStr
from openhands.sdk.llm import LLM

from src.agents.student import build_student_agent_turn
from src.schemas import StudentAgentRequest


request = StudentAgentRequest.model_validate(request_payload)
llm = LLM(
    model="deepseek/deepseek-chat",
    api_key=SecretStr("YOUR_LLM_API_KEY"),
    base_url="https://api.deepseek.com",
    litellm_extra_body={},
)

stages = build_student_agent_turn(request, llm=llm)

final_output = stages["output"]
tool_trace = stages["tool_trace"]
qa_output = stages["qa_output"]
decision_output = stages["decision_output"]
events = stages["events"]
```

## How To Know If It Is Running As A Real Agent

Check these fields:

- `qa_output["answer_source"]`
- `decision_output["decision_source"]`

Interpretation:

- `"llm_agent"`: real LLM-driven agent path
- `"fallback_rule"`: fallback path

Also inspect:

- `tool_trace`

If tool trace contains actual tool calls and both sources are `llm_agent`, then the student chain is running in real agent mode.

## Internal Mechanism Summary

Core files:

- agent entry:
  - [`src\agents\student\agent.py`](/src/agents/student/agent.py)
- response aggregation:
  - [`src\agents\student\response_builder.py`](/src/agents/student/response_builder.py)
- business tools:
  - [`src\tools\search.py`](/src/tools/search.py)
  - [`src\tools\retrieve.py`](/src/tools/retrieve.py)
  - [`src\tools\session.py`](/src/tools/session.py)
  - [`src\tools\memory.py`](/src/tools/memory.py)
  - [`src\tools\game.py`](/src/tools/game.py)
- OpenHands adapters:
  - [`src\tools\openhands\search_tool.py`](/src/tools/openhands/search_tool.py)
  - [`src\tools\openhands\retrieve_tool.py`](/src/tools/openhands/retrieve_tool.py)
  - [`src\tools\openhands\session_tool.py`](/src/tools/openhands/session_tool.py)
  - [`src\tools\openhands\memory_tool.py`](/src/tools/openhands/memory_tool.py)
  - [`src\tools\openhands\game_tool.py`](/src/tools/openhands/game_tool.py)

Current flow:

1. backend builds `StudentAgentRequest`
2. backend provides real `LLM`
3. `StudentOpenHandsAgent` starts OpenHands conversation
4. LLM uses tool loop
5. tool observations are collected from conversation events
6. agent result is normalized into:
   - `qa_output`
   - `decision_output`
7. `response_builder` assembles final `StudentAgentResponse`
8. backend consumes final output

## Current Tool Responsibilities

`search`

- semantic retrieval of lesson context

`retrieve`

- exact fetch by page / section / script block / page number

`session`

- read or update learning session snapshot

`memory`

- read or append QA history

`game`

- generate a grounded multiple-choice quiz when the decision path chooses `trigger_game`
- expose the structured quiz payload through `metadata["game"]`

## Known Operational Notes

1. OpenHands version differences exist across Python environments.
   - The custom student agent already contains compatibility handling for `on_token`.

2. The current demo script uses in-memory demo lesson data.
   - Production backend should pass real `structured_content` and optional `lesson_script`.

3. The student chain is already usable, but prompt stability can still be improved.
   - Tool choice and retrieval specificity may still vary by model behavior.

## Recommended Backend Rollout

Recommended rollout order:

1. Integrate `build_student_agent_turn(...)` in staging and log:
   - `tool_trace`
   - `answer_source`
   - `decision_source`
2. Confirm real LLM path is used.
3. Switch production path to `run_student_agent(...)`.
4. Persist:
   - `updated_session`
   - `updated_progress`
   - `qa_record`
5. Monitor low-quality tool choices and iterate prompt policy if needed.

## Local Validation

Reference runnable script:

- [`scripts\run_student_agent.py`](/scripts/run_student_agent.py)

Run with:

```powershell
python scripts\run_student_agent.py
```

This prints:

- `tool_trace`
- `qa_output`
- `decision_output`
- final response
