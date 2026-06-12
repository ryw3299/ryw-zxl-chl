"""Claude SDK-based student agent runner (non-intrusive replacement).

This module provides drop-in replacements for:
    - run_student_agent()
    - build_student_agent_turn()

It consumes the same ``StudentAgentRequest`` / ``StudentTurnContext`` that the
legacy OpenHands agent consumes, and produces the same ``dict`` shape so that
callers (e.g. ``qa_service.run_qa_interact``) do not need any changes.

Usage in ``src/agents/student/__init__.py`` (switch logic):

    import os
    if os.getenv("STUDENT_AGENT_BACKEND", "openhands").lower() == "claude":
        from src.claude_agents.student_qa import build_student_agent_turn, run_student_agent
    else:
        from .agent import build_student_agent_turn, run_student_agent
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Optional

from src.agents.student.response_builder import build_student_agent_response
from src.schemas import StudentAgentRequest
from src.schemas.common import StructuredLessonContent
from src.schemas.student_turn_context import StudentTurnContext
from src.utils.student.question_classifier import classify_question_type

# Claude SDK infra
try:
    from claude_sdk.infra.agent_factory import AgentFactory
except ImportError as _import_err:
    raise ImportError(
        "claude_sdk infra could not be imported. "
        "Ensure the claude_agent_sdk package is installed in this environment."
    ) from _import_err


# ----------------------------------------------------------------------
# Public API (signature-compatible with agent.py)
# ----------------------------------------------------------------------


def run_student_agent(request: StudentAgentRequest | dict, *, llm: Any = None) -> dict:
    """Synchronous entry point — same signature as OpenHands version."""
    stages = build_student_agent_turn(request, llm=llm)
    return stages["output"].model_dump(mode="python")


def build_student_agent_turn(
    request: StudentAgentRequest | dict,
    *,
    llm: Any = None,
) -> dict[str, Any]:
    """Run one student turn via Claude SDK.

    Returns a dict with the same keys as the OpenHands path so that
    ``qa_service`` can consume it without any modifications.
    """
    validated = (
        request if isinstance(request, StudentAgentRequest) else StudentAgentRequest.model_validate(request)
    )

    turn_context = validated.turn_context
    if turn_context is None:
        if validated.structured_content is not None:
            sc = validated.structured_content
            if isinstance(sc, dict):
                sc = StructuredLessonContent.model_validate(sc)
            turn_context = StudentTurnContext(
                session_id=validated.session_id,
                user_id="",
                course_id=validated.course_id or "",
                lesson_id=validated.lesson_id,
                question=validated.question,
                question_type=classify_question_type(validated.question),
                current_section_id=validated.current_section_id,
                current_page=validated.current_page,
                current_script_block_id=validated.current_script_block_id,
                structured_content=sc,
                lesson_script=validated.lesson_script,
                recent_turns=validated.history_qa or [],
            )
        else:
            raise ValueError(
                "Claude SDK runner requires turn_context (or structured_content as fallback). "
                "Ensure qa_service.build_turn_context() ran before calling the agent."
            )

    # Run the async pipeline via asyncio.run (FastAPI sync routes are OK with this
    # because the OpenHands path already uses anyio.run internally).
    return asyncio.run(_run_claude_turn(validated, turn_context))


# ----------------------------------------------------------------------
# Async core
# ----------------------------------------------------------------------


async def _run_claude_turn(
    request: StudentAgentRequest,
    ctx: StudentTurnContext,
) -> dict[str, Any]:
    project_root = _resolve_claude_sdk_root()

    agent = AgentFactory.create_agent(
        agent_name="student_qa",
        cwd=str(Path(__file__).resolve().parents[2]),  # -> project root
        workspace=str(project_root.parent / "data" / "student_qa_runs" / ctx.session_id),
        project_root=str(project_root),
        skills=["student_qa"],
        # We keep allowed_tools minimal; the student QA turn is primarily
        # a single JSON-generation call grounded in pre-retrieved context.
        tools=["Read", "Write", "Edit"],
        provider=_get_provider_name(),
        model=os.getenv("CLAUDE_MODEL") or os.getenv("ANTHROPIC_MODEL") or None,
    )

    await agent.start()

    try:
        prompt = _build_context_turn_prompt(ctx)
        raw_output = await agent.ask_with_retry(
            prompt,
            timeout=float(os.getenv("CLAUDE_ASK_TIMEOUT", "60.0")),
        )
    finally:
        await agent.close()

    qa_output, decision_output = _parse_claude_response(raw_output, ctx)

    response = build_student_agent_response(
        request,
        qa_output,
        decision_output,
        metadata={
            "framework": "claude_sdk",
            "path": "context",
            "tool_trace": [],
            "conversation_event_count": 1,
        },
    )

    return {
        "request": request,
        "qa_output": qa_output,
        "decision_output": decision_output,
        "tool_trace": [],
        "output": response,
        "events": [],
    }


# ----------------------------------------------------------------------
# Prompt builder (mirrors agent.py _build_context_turn_prompt)
# ----------------------------------------------------------------------


def _build_context_turn_prompt(ctx: StudentTurnContext) -> str:
    """Build a user prompt for the context-based path."""
    context_parts: list[str] = []
    if ctx.exact_source:
        context_parts.append(
            f"【精读内容】{ctx.exact_source.title or ctx.exact_source.source_id}: "
            f"{_clean_text(ctx.exact_source.text, 400)}"
        )
    for i, chunk in enumerate(ctx.retrieved_chunks[:3]):
        if chunk != ctx.exact_source:
            context_parts.append(
                f"【参考{i + 1}】{chunk.title or chunk.source_id}: {_clean_text(chunk.text, 200)}"
            )

    history_snippet = ""
    if ctx.recent_turns:
        recent = ctx.recent_turns[-3:]
        history_snippet = "Recent QA history:\n" + "\n".join(
            f"- Q: {t.get('question', '')} A: {str(t.get('answer', ''))[:80]}" for t in recent
        )

    return f"""Student question: {ctx.question}

Lesson ID: {ctx.lesson_id}
Session ID: {ctx.session_id}
Current section: {ctx.current_section_id}
Current page: {ctx.current_page}

Retrieved context:
{chr(10).join(context_parts) if context_parts else "(No retrieval match)"}

{history_snippet}

Based on the retrieved context above, respond with JSON only:
{{
  "answer": "student-facing Chinese answer",
  "understanding_level": "full|partial|none|null",
  "recommended_narration_level": "A|B|C|D|null",
  "next_action": "resume|supplement_then_resume|reteach_slowly|trigger_game",
  "reason": "short Chinese explanation"
}}

Choose recommended_narration_level based on the student's apparent understanding,
the question type, and how much explanation would help next:
- A = most detailed
- B = detailed
- C = concise
- D = shortest

Do not fabricate identifiers. If a value is unknown, use null.""".strip()


# ----------------------------------------------------------------------
# Response parser
# ----------------------------------------------------------------------


def _parse_claude_response(
    raw_output: str,
    ctx: StudentTurnContext,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract qa_output and decision_output from the agent's JSON text."""
    payload = _extract_json_dict(raw_output)

    answer = str(payload.get("answer", "")).strip()
    understanding_level = _normalize_level(payload.get("understanding_level"))
    recommended_narration_level = _normalize_narration_level(payload.get("recommended_narration_level"))
    next_action = _normalize_next_action(payload.get("next_action"))

    if recommended_narration_level is None:
        recommended_narration_level = _fallback_narration_level(
            question=ctx.question,
            question_type=ctx.question_type or "unknown",
            understanding_level=understanding_level,
        )

    # Fallback answer if JSON is broken or empty
    if not answer:
        sc = ctx.structured_content
        if sc and sc.lesson_summary.strip():
            answer = f"我先根据当前课时内容给出概括：{sc.lesson_summary.strip()}"
        else:
            answer = "抱歉，我暂时没有拿到足够的课时上下文来回答这个问题。"

    # Matched fields fall back to current context (response_builder will refine)
    matched_section_id = ctx.current_section_id
    matched_page = ctx.current_page
    matched_script_block_id = ctx.current_script_block_id

    qa_output: dict[str, Any] = {
        "status": "success",
        "message": "qa stage finished via claude sdk",
        "answer": answer,
        "references": [],
        "understanding_level": understanding_level,
        "recommended_narration_level": recommended_narration_level,
        "matched_section_id": matched_section_id,
        "matched_page": matched_page,
        "matched_script_block_id": matched_script_block_id,
        "skill_name": ctx.question_type or "summary",
        "answer_source": "claude_sdk",
    }

    reason = str(payload.get("reason", "")).strip()
    if not reason:
        reason = _default_reason(next_action)

    decision_output: dict[str, Any] = {
        "status": "success",
        "message": "decision stage finished via claude sdk",
        "next_action": next_action,
        "reason": reason,
        "target_section_id": payload.get("target_section_id") or matched_section_id,
        "target_page": (
            payload.get("target_page") if payload.get("target_page") is not None else matched_page
        ),
        "target_script_block_id": (payload.get("target_script_block_id") or matched_script_block_id),
        "decision_source": "claude_sdk",
    }

    return qa_output, decision_output


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------


def _resolve_claude_sdk_root() -> Path:
    """Return the path to the claude_sdk package root inside ChaoXingAgent."""
    # src/claude_agents/student_qa.py -> ../../claude_sdk
    return Path(__file__).resolve().parents[2] / "claude_sdk"


def _get_provider_name() -> str:
    """Read provider from env, defaulting to xfyun (DeepSeek via Anthropic-compatible endpoint)."""
    return os.getenv("CLAUDE_PROVIDER", "xfyun")


def _extract_json_dict(text: str) -> dict[str, Any]:
    """Robustly extract the first JSON object from LLM text output."""
    if not text:
        return {}
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*?\}", cleaned, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return {}


def _normalize_level(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        v = value.lower()
        if v in ("full", "partial", "none"):
            return v
    return None


def _normalize_next_action(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        v = value.lower()
        if v in ("resume", "supplement_then_resume", "reteach_slowly", "trigger_game"):
            return v
    return "resume"


def _normalize_narration_level(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip().upper()
        if v in ("A", "B", "C", "D"):
            return v
    return None


def _fallback_narration_level(
    *,
    question: str,
    question_type: str,
    understanding_level: Optional[str],
) -> str:
    normalized_question = (question or "").strip()
    hard_question_markers = (
        "为什么",
        "为何",
        "怎么推",
        "如何推",
        "推导",
        "证明",
        "区别",
        "联系",
        "为什么不是",
        "怎么算",
        "怎么理解",
        "why",
        "how",
        "prove",
        "derive",
        "difference",
    )
    is_harder_question = len(normalized_question) >= 24 or any(
        marker in normalized_question.lower() for marker in hard_question_markers
    )

    if understanding_level == "none":
        return "A"
    if understanding_level == "full":
        return "D"
    if understanding_level == "partial":
        if question_type in {"reasoning", "procedure", "comparison"} or is_harder_question:
            return "B"
        return "C"

    if question_type in {"reasoning", "procedure", "comparison"}:
        return "B"
    if is_harder_question:
        return "B"
    return "C"


def _default_reason(next_action: Optional[str]) -> str:
    reasons = {
        "resume": "当前问题已被覆盖，继续原学习进度。",
        "supplement_then_resume": "先补充解释当前知识点，再回到原学习进度。",
        "reteach_slowly": "当前证据不足或理解度偏低，需要放慢节奏重新讲解。",
        "trigger_game": "当前更适合通过轻量互动来巩固理解。",
    }
    return reasons.get(next_action or "", "继续学习进度。")


def _clean_text(text: str, limit: int = 220) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."
