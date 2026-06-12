from __future__ import annotations

import json
import logging
import re
import tempfile
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from openhands.sdk.agent import Agent
from openhands.sdk.conversation import Conversation
from openhands.sdk.conversation.state import ConversationExecutionStatus
from openhands.sdk.event import ActionEvent, MessageEvent, ObservationEvent
from openhands.sdk.llm import LLM, Message, TextContent, content_to_str
from openhands.sdk.tool import Tool
from pydantic import PrivateAttr

from src.agents.student.response_builder import build_student_agent_response

# Legacy imports -- only needed when the old from_request path is used
from src.memory.history import QAHistoryStore
from src.memory.session_store import SessionStore
from src.schemas import (
    QARecord,
    ReferenceItem,
    RetrievedContextItem,
    StudentAgentRequest,
    StudentAgentResponse,
    StudentQuestionType,
)
from src.schemas.student_turn_context import StudentTurnContext
from src.services.student.conversation_service import ConversationService
from src.skills import get_skill_content
from src.tools.openhands.game_tool import GameAction
from src.tools.openhands.memory_tool import MemoryAction
from src.tools.openhands.retrieve_tool import RetrieveAction
from src.tools.openhands.search_tool import SearchAction
from src.tools.openhands.session_tool import SessionAction
from src.utils.student.question_classifier import classify_question_type

logger = logging.getLogger(__name__)


SKILL_DISPLAY_NAMES: dict[str, str] = {
    "definition": "定义式讲解",
    "reasoning": "因果式讲解",
    "procedure": "步骤式讲解",
    "example": "例子驱动讲解",
    "comparison": "对比式讲解",
    "summary": "总结式讲解",
    "quiz": "测验式讲解",
    "game": "互动式讲解",
}

DECISION_REASONS: dict[Optional[str], str] = {
    "supplement_then_resume": "先补充解释当前知识点，再回到原学习进度。",
    "reteach_slowly": "当前证据不足或理解度偏低，需要放慢节奏重新讲解。",
    "trigger_game": "当前更适合通过轻量互动来巩固理解。",
    "resume": "当前问题已经被覆盖，可以继续原学习进度。",
    None: "当前未生成下一步动作。",
}

ALLOWED_NEXT_ACTIONS = frozenset({"resume", "supplement_then_resume", "reteach_slowly", "trigger_game"})

PLACEHOLDER_API_KEY_MARKERS = frozenset({"test", "fake", "placeholder", "mock", ""})

# Re-export for backward compatibility with tests
_classify_question_type = classify_question_type

# Re-export kept for old imports (e.g. QUESTION_TYPE_KEYWORDS used in tests)


class StudentOpenHandsAgent(Agent):
    """OpenHands student agent with LLM-driven answer synthesis.

    Supports two construction modes:

    * ``from_context(turn_context)`` -- **new path**: the backend has
      already run session lookup, RAG retrieval, and history loading.
      Only the ``game`` tool is registered.
    * ``from_request(request)`` -- **legacy path**: all five tools are
      registered and the agent drives the full pipeline itself.
    """

    _request: Optional[StudentAgentRequest] = PrivateAttr(default=None)
    _turn_context: Optional[StudentTurnContext] = PrivateAttr(default=None)
    _qa_output: dict[str, Any] = PrivateAttr(default_factory=dict)
    _decision_output: dict[str, Any] = PrivateAttr(default_factory=dict)
    _tool_trace: list[dict[str, Any]] = PrivateAttr(default_factory=list)
    _finalized: bool = PrivateAttr(default=False)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    @classmethod
    def from_context(
        cls,
        turn_context: StudentTurnContext,
        *,
        llm: Optional[LLM] = None,
    ) -> StudentOpenHandsAgent:
        """Create an agent that consumes a pre-assembled ``TurnContext``.

        Only the ``game`` tool is registered; search / retrieve / session /
        memory are handled by the backend before this point.
        """
        tools: list[Tool] = []
        if turn_context.structured_content is not None:
            tools.append(
                Tool(
                    name="game",
                    params={"structured_content": turn_context.structured_content},
                )
            )

        agent = cls(llm=llm or _build_placeholder_llm(), tools=tools)
        agent._turn_context = turn_context
        return agent

    @classmethod
    def from_request(
        cls,
        request: StudentAgentRequest,
        *,
        session_db_path: str,
        history_db_path: str,
        llm: Optional[LLM] = None,
    ) -> StudentOpenHandsAgent:
        """Legacy constructor -- registers all five tools."""
        tools: list[Tool] = []
        if request.structured_content is not None:
            tools.extend(
                [
                    Tool(
                        name="search",
                        params={
                            "structured_content": request.structured_content,
                            "lesson_script": request.lesson_script,
                        },
                    ),
                    Tool(
                        name="retrieve",
                        params={
                            "structured_content": request.structured_content,
                            "lesson_script": request.lesson_script,
                        },
                    ),
                    Tool(
                        name="game",
                        params={"structured_content": request.structured_content},
                    ),
                ]
            )
        tools.extend(
            [
                Tool(name="session", params={"session_db_path": session_db_path}),
                Tool(name="memory", params={"history_db_path": history_db_path}),
            ]
        )
        agent = cls(llm=llm or _build_placeholder_llm(), tools=tools)
        agent._request = request
        return agent

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    @property
    def qa_output(self) -> dict[str, Any]:
        return dict(self._qa_output)

    @property
    def decision_output(self) -> dict[str, Any]:
        return dict(self._decision_output)

    @property
    def tool_trace(self) -> list[dict[str, Any]]:
        return list(self._tool_trace)

    def _get_question(self) -> str:
        if self._turn_context:
            return self._turn_context.question
        return self._request.question  # type: ignore[union-attr]

    def _get_lesson_id(self) -> str:
        if self._turn_context:
            return self._turn_context.lesson_id
        return self._request.lesson_id  # type: ignore[union-attr]

    def _get_session_id(self) -> str:
        if self._turn_context:
            return self._turn_context.session_id
        return self._request.session_id  # type: ignore[union-attr]

    # ------------------------------------------------------------------
    # Step / fallback
    # ------------------------------------------------------------------

    def step(
        self,
        conversation,
        on_event,
        on_token: Any | None = None,
    ) -> None:  # type: ignore[override]
        if _is_placeholder_llm(self.llm):
            self._run_fallback_step(conversation, on_event)
            return

        try:
            super().step(conversation, on_event=on_event, on_token=on_token)
        except TypeError as exc:
            if "on_token" not in str(exc):
                raise
            super().step(conversation, on_event=on_event)
        if conversation.state.execution_status == ConversationExecutionStatus.FINISHED:
            events = list(conversation.state.events)
            has_tool_activity = any(isinstance(event, (ActionEvent, ObservationEvent)) for event in events)
            if not has_tool_activity:
                self._run_fallback_step(conversation, on_event)
                return
            self._finalize_agent_run(conversation, on_event=on_event)

    def _run_fallback_step(self, conversation, on_event) -> None:
        """Generate answer and decision using pre-assembled context or legacy tools."""
        if self._turn_context is not None:
            self._run_context_fallback(conversation, on_event)
        else:
            self._run_legacy_fallback(conversation, on_event)

    # ------------------------------------------------------------------
    # NEW PATH: context-based fallback (no tool calls for search/retrieve/session/memory)
    # ------------------------------------------------------------------

    def _run_context_fallback(self, conversation, on_event) -> None:
        ctx = self._turn_context
        assert ctx is not None

        question = ctx.question
        question_type = ctx.question_type or classify_question_type(question)
        skill_name = question_type if question_type != "unknown" else "summary"

        # Handle chitchat / greetings without retrieval
        if question_type == "chitchat":
            self._handle_chitchat(ctx, question, conversation, on_event)
            return

        session = ctx.session_snapshot
        candidates = ctx.retrieved_chunks
        exact_item = ctx.exact_source
        history_records = ctx.recent_turns

        sc = ctx.structured_content
        has_lesson_context = bool(sc and (sc.pages or sc.sections or sc.lesson_summary.strip()))

        references = _build_references(candidates, exact_item)
        if not references:
            references = [_build_fallback_reference_from_context(ctx)]
        understanding_level = _infer_understanding_level(
            question_type,
            exact_item,
            len(candidates),
            has_lesson_context=has_lesson_context,
        )

        fallback_answer = _compose_answer_from_context(
            ctx,
            question=question,
            question_type=question_type,
            skill_name=skill_name,
            exact_item=exact_item,
            candidates=candidates,
            history_records=history_records,
        )
        answer, answer_source = _llm_synthesize_answer(
            llm=self.llm,
            question=question,
            question_type=question_type,
            skill_name=skill_name,
            exact_item=exact_item,
            candidates=candidates,
            history_records=history_records,
            fallback_answer=fallback_answer,
        )

        primary = candidates[0] if candidates else None
        matched_section_id, matched_page, matched_script_block_id = _resolve_grounding(
            exact_item=exact_item,
            primary=primary,
            session=session,
            request_section_id=ctx.current_section_id,
            request_page=ctx.current_page,
            request_script_block_id=ctx.current_script_block_id,
        )

        self._qa_output = {
            "status": "success",
            "message": "qa stage finished via context-based path",
            "answer": answer,
            "references": references,
            "understanding_level": understanding_level,
            "matched_section_id": matched_section_id,
            "matched_page": matched_page,
            "matched_script_block_id": matched_script_block_id,
            "skill_name": skill_name,
            "answer_source": answer_source,
        }

        decision_result = _decide_next_action_via_llm_ctx(
            ctx=ctx,
            question=question,
            question_type=question_type,
            understanding_level=understanding_level,
            matched_section_id=matched_section_id,
            matched_page=matched_page,
            matched_script_block_id=matched_script_block_id,
            history_records=history_records,
            llm=self.llm,
        )
        self._decision_output = {
            "status": "success",
            "message": f"decision stage finished ({decision_result.get('decision_source', 'unknown')})",
            "next_action": decision_result["next_action"],
            "reason": decision_result["reason"],
            "target_section_id": decision_result["target_section_id"],
            "target_page": decision_result["target_page"],
            "target_script_block_id": decision_result["target_script_block_id"],
            "decision_source": decision_result.get("decision_source", "unknown"),
        }
        next_action = decision_result["next_action"]

        if next_action == "trigger_game" and "game" in self.tools_map:
            self._execute_tool(
                "game",
                GameAction(
                    question=question,
                    lesson_id=ctx.lesson_id,
                    session_id=ctx.session_id,
                    section_id=matched_section_id,
                    page=matched_page,
                ),
                conversation,
                on_event,
            )

        on_event(
            MessageEvent(
                source="agent",
                llm_message=Message(
                    role="assistant",
                    content=[
                        TextContent(
                            text=_build_agent_message(answer, next_action, session),
                        )
                    ],
                ),
            )
        )
        conversation.state.execution_status = ConversationExecutionStatus.FINISHED
        self._finalized = True

    # ------------------------------------------------------------------
    # LEGACY PATH: tool-based fallback (kept for backward compat)
    def _handle_chitchat(self, ctx, question, conversation, on_event) -> None:
        """Respond to greetings / casual chat without invoking retrieval."""
        CHITCHAT_REPLIES = {
            "你好": "你好！我是你的课程学习助手，有什么关于课程内容的问题可以问我。",
            "您好": "您好！有什么课程相关的问题我可以帮你解答？",
            "你是谁": "我是你的AI课程学习助手，可以帮你解答课程中的知识点问题、进行知识检测和互动学习。有什么想了解的，直接问我就好！",
            "你是什么": "我是基于课程内容训练的AI学习助手，能帮你理解课件中的知识点、回答学习问题。试试问我一个课程相关的问题吧！",
            "你叫什么": "我是你的AI课程学习助手，你可以叫我小助手。有课程问题尽管问我！",
            "你能做什么": "我可以帮你：1. 解答课程知识点问题 2. 用不同方式讲解难点 3. 通过小测验巩固理解。试试问我一个问题吧！",
            "谢谢": "不客气！如果还有其他问题，随时可以问我。",
            "好的": "好的，有其他问题可以继续问我。",
            "明白了": "很好！如果还有不清楚的地方，随时提问。",
            "懂了": "太好了！有其他知识点想深入了解的话，可以继续提问。",
        }
        normalized = question.strip()
        reply = CHITCHAT_REPLIES.get(normalized, "你好！我是课程学习助手。请问有什么关于课程内容的问题吗？")

        self._qa_output = {
            "status": "success",
            "message": "chitchat response",
            "answer": reply,
            "references": [],
            "understanding_level": None,
            "matched_section_id": None,
            "matched_page": None,
            "matched_script_block_id": None,
            "skill_name": "chitchat",
            "answer_source": "chitchat",
        }
        self._decision_output = {
            "status": "success",
            "message": "chitchat - no decision needed",
            "next_action": "resume",
            "reason": "闲聊回复，继续学习进度。",
            "target_section_id": ctx.current_section_id,
            "target_page": ctx.current_page,
            "target_script_block_id": ctx.current_script_block_id,
            "decision_source": "chitchat",
        }

        on_event(
            MessageEvent(
                source="agent",
                llm_message=Message(
                    role="assistant",
                    content=[TextContent(text=reply)],
                ),
            )
        )
        conversation.state.execution_status = ConversationExecutionStatus.FINISHED
        self._finalized = True

    # ------------------------------------------------------------------

    def _run_legacy_fallback(self, conversation, on_event) -> None:
        request = self._request
        assert request is not None
        question = request.question
        question_type = classify_question_type(question)
        skill_name = question_type if question_type != "unknown" else "summary"

        session_obs = self._execute_tool(
            "session",
            SessionAction(command="get", session_id=request.session_id),
            conversation,
            on_event,
        )
        session = session_obs.session or _build_base_session(request)

        search_obs = self._execute_tool(
            "search",
            SearchAction(
                query=question,
                top_k=5,
                prefer_section_id=session.current_section_id or request.current_section_id,
                prefer_page=session.current_page or request.current_page,
                prefer_script_block_id=session.current_script_block_id or request.current_script_block_id,
                include_script=True,
            ),
            conversation,
            on_event,
        )

        primary = _choose_primary_candidate(search_obs.results, session, request)
        retrieve_obs = None
        if primary is not None:
            retrieve_obs = self._execute_tool(
                "retrieve",
                _build_retrieve_action(primary),
                conversation,
                on_event,
            )
        elif session.current_script_block_id:
            retrieve_obs = self._execute_tool(
                "retrieve",
                RetrieveAction(script_block_id=session.current_script_block_id),
                conversation,
                on_event,
            )
        elif session.current_page is not None:
            retrieve_obs = self._execute_tool(
                "retrieve",
                RetrieveAction(page=session.current_page),
                conversation,
                on_event,
            )
        elif session.current_section_id:
            retrieve_obs = self._execute_tool(
                "retrieve",
                RetrieveAction(section_id=session.current_section_id),
                conversation,
                on_event,
            )

        history_obs = self._execute_tool(
            "memory",
            MemoryAction(command="get_history", session_id=request.session_id, limit=5),
            conversation,
            on_event,
        )

        exact_item = (
            _observation_to_context_item(retrieve_obs) if retrieve_obs and not retrieve_obs.is_error else None
        )
        references = _build_references(search_obs.results, exact_item)
        if not references:
            references = [_build_fallback_reference(request)]

        sc = request.structured_content
        has_lesson_context = bool(sc and (sc.pages or sc.sections or sc.lesson_summary.strip()))
        understanding_level = _infer_understanding_level(
            question_type,
            exact_item,
            search_obs.total,
            has_lesson_context=has_lesson_context,
        )

        fallback_answer = _compose_answer(
            request,
            question=question,
            question_type=question_type,
            skill_name=skill_name,
            exact_item=exact_item,
            candidates=search_obs.results,
            history_records=history_obs.records,
        )
        answer, answer_source = _llm_synthesize_answer(
            llm=self.llm,
            question=question,
            question_type=question_type,
            skill_name=skill_name,
            exact_item=exact_item,
            candidates=search_obs.results,
            history_records=history_obs.records,
            fallback_answer=fallback_answer,
        )

        matched_section_id, matched_page, matched_script_block_id = _resolve_grounding(
            exact_item=exact_item,
            primary=primary,
            session=session,
            request_section_id=request.current_section_id,
            request_page=request.current_page,
            request_script_block_id=request.current_script_block_id,
        )

        self._qa_output = {
            "status": "success",
            "message": "qa stage finished via openhands",
            "answer": answer,
            "references": references,
            "understanding_level": understanding_level,
            "matched_section_id": matched_section_id,
            "matched_page": matched_page,
            "matched_script_block_id": matched_script_block_id,
            "skill_name": skill_name,
            "answer_source": answer_source,
        }

        decision_result = _decide_next_action_via_llm(
            request=request,
            question=question,
            question_type=question_type,
            understanding_level=understanding_level,
            matched_section_id=matched_section_id,
            matched_page=matched_page,
            matched_script_block_id=matched_script_block_id,
            history_records=history_obs.records,
            llm=self.llm,
        )
        self._decision_output = {
            "status": "success",
            "message": f"decision stage finished via openhands ({decision_result.get('decision_source', 'unknown')})",
            "next_action": decision_result["next_action"],
            "reason": decision_result["reason"],
            "target_section_id": decision_result["target_section_id"],
            "target_page": decision_result["target_page"],
            "target_script_block_id": decision_result["target_script_block_id"],
            "decision_source": decision_result.get("decision_source", "unknown"),
        }
        next_action = decision_result["next_action"]

        on_event(
            MessageEvent(
                source="agent",
                llm_message=Message(
                    role="assistant",
                    content=[
                        TextContent(
                            text=_build_agent_message(answer, next_action, _build_base_session(request))
                        )
                    ],
                ),
            )
        )
        conversation.state.execution_status = ConversationExecutionStatus.FINISHED
        self._finalized = True

    # ------------------------------------------------------------------
    # Finalization / ensure
    # ------------------------------------------------------------------

    def ensure_finalized(self, conversation, on_event) -> None:
        if self._finalized and self._qa_output and self._decision_output:
            return

        events = list(conversation.state.events)
        has_tool_activity = any(isinstance(event, (ActionEvent, ObservationEvent)) for event in events)
        has_agent_message = any(
            isinstance(event, MessageEvent) and event.source == "agent" for event in events
        )

        if has_tool_activity or has_agent_message:
            self._finalize_agent_run(conversation, on_event=on_event)

        if not self._qa_output or not self._decision_output:
            self._run_fallback_step(conversation, on_event)

    def _finalize_agent_run(self, conversation, on_event=None) -> None:
        """Aggregate the conversation into ``_qa_output`` / ``_decision_output``.

        Called once the agent's main loop terminates.  The optional
        ``on_event`` callback is forwarded to ``_execute_tool`` only when
        the LLM payload requests a delayed ``trigger_game``; if absent we
        substitute a no-op so the tool can still run silently.
        """
        if self._finalized:
            return

        events = list(conversation.state.events)
        tool_state = _collect_tool_state(events)
        self._tool_trace = _extract_tool_trace(events)

        question = self._get_question()
        question_type = classify_question_type(question)
        skill_name = question_type if question_type != "unknown" else "summary"

        if self._turn_context is not None:
            ctx = self._turn_context
            session = ctx.session_snapshot or (tool_state.get("session"))
            search_results = ctx.retrieved_chunks or tool_state.get("search_results", [])
            search_total = len(search_results)
            exact_item = ctx.exact_source or tool_state.get("exact_item")
            sc = ctx.structured_content
            current_section_id = ctx.current_section_id
            current_page = ctx.current_page
            current_script_block_id = ctx.current_script_block_id
        else:
            request = self._request
            assert request is not None
            session = tool_state.get("session") or _build_base_session(request)
            search_results = tool_state.get("search_results", [])
            search_total = tool_state.get("search_total", len(search_results))
            exact_item = tool_state.get("exact_item")
            sc = request.structured_content
            current_section_id = request.current_section_id
            current_page = request.current_page
            current_script_block_id = request.current_script_block_id

        has_lesson_context = bool(sc and (sc.pages or sc.sections or sc.lesson_summary.strip()))

        primary = search_results[0] if search_results else None

        references = _build_references(search_results, exact_item)
        if not references:
            if self._turn_context:
                references = [_build_fallback_reference_from_context(self._turn_context)]
            elif self._request and self._request.structured_content:
                references = [_build_fallback_reference(self._request)]

        understanding_level = _infer_understanding_level(
            question_type,
            exact_item,
            search_total,
            has_lesson_context=has_lesson_context,
        )

        payload = _parse_agent_payload(_get_latest_agent_message_text(events))
        payload_understanding = _normalize_understanding_level_local(payload.get("understanding_level"))

        # Grounding priority: evidence > session > request > LLM payload (last, may hallucinate)
        matched_section_id, matched_page, matched_script_block_id = _resolve_grounding(
            exact_item=exact_item,
            primary=primary,
            session=session,
            request_section_id=current_section_id,
            request_page=current_page,
            request_script_block_id=current_script_block_id,
            payload_section_id=payload.get("matched_section_id"),
            payload_page=payload.get("matched_page"),
            payload_script_block_id=payload.get("matched_script_block_id"),
        )

        fallback_answer = ""
        if sc:
            if exact_item is None and not search_results:
                summary = sc.lesson_summary.strip()
                fallback_answer = (
                    f"我先根据当前课时内容给出概括：{summary}"
                    if summary
                    else "我暂时没有拿到足够的课时上下文。"
                )
            else:
                fb_primary = exact_item or search_results[0]
                style = SKILL_DISPLAY_NAMES.get(skill_name, skill_name)
                topic = fb_primary.title or "当前知识点"
                snippet = _clean_text(fb_primary.text, 220)
                fallback_answer = f"先用{style}回答你的问题。围绕「{topic}」，当前课时内容显示：{snippet}"

        answer = str(payload.get("answer") or "").strip() or fallback_answer
        answer_source = "llm_agent" if str(payload.get("answer") or "").strip() else "fallback_rule"
        normalized_next_action = _normalize_next_action_local(payload.get("next_action"))
        next_action = normalized_next_action or _decide_next_action_rule(
            question_type,
            payload_understanding or understanding_level,
        )
        decision_source = "llm_agent" if normalized_next_action else "fallback_rule"
        reason = str(payload.get("reason") or "").strip() or DECISION_REASONS[next_action]

        self._qa_output = {
            "status": "success",
            "message": "qa stage finished via openhands agent loop",
            "answer": answer,
            "references": references,
            "understanding_level": payload_understanding or understanding_level,
            "matched_section_id": matched_section_id,
            "matched_page": matched_page,
            "matched_script_block_id": matched_script_block_id,
            "skill_name": skill_name,
            "answer_source": answer_source,
            "question_type": question_type,
        }
        self._decision_output = {
            "status": "success",
            "message": f"decision stage finished via openhands ({decision_source})",
            "next_action": next_action,
            "reason": reason,
            "target_section_id": payload.get("target_section_id") or matched_section_id,
            "target_page": payload.get("target_page")
            if payload.get("target_page") is not None
            else matched_page,
            "target_script_block_id": payload.get("target_script_block_id") or matched_script_block_id,
            "decision_source": decision_source,
        }
        if (
            next_action == "trigger_game"
            and "game" in self.tools_map
            and "game" not in [item["tool"] for item in self._tool_trace]
        ):
            target_page = (
                payload.get("target_page") if payload.get("target_page") is not None else matched_page
            )
            self._execute_tool(
                "game",
                GameAction(
                    question=question,
                    lesson_id=self._get_lesson_id(),
                    session_id=self._get_session_id(),
                    section_id=matched_section_id,
                    page=target_page,
                ),
                conversation,
                on_event if callable(on_event) else lambda _: None,
            )
        self._finalized = True

    def _execute_tool(self, tool_name: str, action, conversation, on_event):
        tool = self.tools_map[tool_name]
        observation = tool(action, conversation)
        if callable(on_event):
            on_event(
                ObservationEvent(
                    tool_name=tool_name,
                    tool_call_id=str(uuid4()),
                    action_id=str(uuid4()),
                    observation=observation,
                )
            )
        self._tool_trace.append(
            {
                "tool": tool_name,
                "action": action.model_dump(mode="python"),
                "is_error": observation.is_error,
                "content": observation.text,
            }
        )
        return observation


# =====================================================================
# Public entry points
# =====================================================================


def run_student_agent(request: StudentAgentRequest | dict, *, llm: Optional[LLM] = None) -> dict:
    stages = build_student_agent_turn(request, llm=llm)
    return stages["output"].model_dump(mode="python")


def build_student_agent_turn(
    request: StudentAgentRequest | dict,
    *,
    llm: Optional[LLM] = None,
) -> dict[str, Any]:
    validated_request = (
        request if isinstance(request, StudentAgentRequest) else StudentAgentRequest.model_validate(request)
    )

    turn_context = validated_request.turn_context

    if turn_context is not None:
        return _build_turn_with_context(validated_request, turn_context, llm=llm)

    return _build_turn_legacy(validated_request, llm=llm)


def _build_turn_with_context(
    validated_request: StudentAgentRequest,
    turn_context: StudentTurnContext,
    *,
    llm: Optional[LLM] = None,
) -> dict[str, Any]:
    """New path: context already assembled by the backend."""
    conv_service = ConversationService()
    conv_dir = conv_service.get_conversation_dir(turn_context.session_id)
    workspace = conv_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    agent = StudentOpenHandsAgent.from_context(turn_context, llm=llm)
    conversation = Conversation(
        agent=agent,
        workspace=workspace,
        persistence_dir=conv_dir / "openhands",
        visualizer=None,
        stuck_detection=False,
        max_iteration_per_run=8,
    )

    user_message = (
        turn_context.question if _is_placeholder_llm(agent.llm) else _build_context_turn_prompt(turn_context)
    )
    conversation.send_message(user_message)
    conversation.run()
    agent.ensure_finalized(conversation, conversation._on_event)

    response = build_student_agent_response(
        validated_request,
        agent.qa_output,
        agent.decision_output,
        metadata={
            "framework": "openhands",
            "path": "context",
            "tool_trace": agent.tool_trace,
            "game": _extract_game_payload(list(conversation.state.events), agent.tool_trace),
            "conversation_event_count": len(list(conversation.state.events)),
        },
    )
    canonical_question_type = classify_question_type(validated_request.question)
    if response.question_type != canonical_question_type or response.question_type == "unknown":
        response = response.model_copy(
            update={
                "question_type": canonical_question_type,
                "suggested_questions": _build_suggested_questions(
                    canonical_question_type,
                    response.matched_knowledge_points,
                ),
            }
        )

    conv_service.append_turn(
        turn_context.session_id,
        {
            "question": turn_context.question,
            "answer": response.answer,
            "understanding_level": response.understanding_level,
            "current_section_id": response.matched_section_id,
            "current_page": response.matched_page,
        },
    )

    return {
        "request": validated_request,
        "qa_output": agent.qa_output,
        "decision_output": agent.decision_output,
        "tool_trace": agent.tool_trace,
        "output": response,
        "events": list(conversation.state.events),
    }


def _build_turn_legacy(
    validated_request: StudentAgentRequest,
    *,
    llm: Optional[LLM] = None,
) -> dict[str, Any]:
    """Legacy path: agent drives the full tool pipeline."""
    with tempfile.TemporaryDirectory(prefix="student-agent-") as temp_dir:
        temp_path = Path(temp_dir)
        session_store = SessionStore(str(temp_path / "sessions.db"))
        history_store = QAHistoryStore(str(temp_path / "history.db"))

        session_store.save(_build_base_session(validated_request))
        _seed_history_store(history_store, validated_request)

        agent = StudentOpenHandsAgent.from_request(
            validated_request,
            session_db_path=str(temp_path / "sessions.db"),
            history_db_path=str(temp_path / "history.db"),
            llm=llm,
        )
        conversation = Conversation(
            agent=agent,
            workspace=temp_path / "workspace",
            persistence_dir=None,
            visualizer=None,
            stuck_detection=False,
            max_iteration_per_run=8,
        )
        user_message = (
            validated_request.question
            if _is_placeholder_llm(agent.llm)
            else _build_student_turn_prompt(validated_request)
        )
        conversation.send_message(user_message)
        conversation.run()
        agent.ensure_finalized(conversation, conversation._on_event)

        response = build_student_agent_response(
            validated_request,
            agent.qa_output,
            agent.decision_output,
            metadata={
                "framework": "openhands",
                "path": "legacy",
                "tool_trace": agent.tool_trace,
                "game": _extract_game_payload(list(conversation.state.events), agent.tool_trace),
                "conversation_event_count": len(list(conversation.state.events)),
            },
        )
        canonical_question_type = classify_question_type(validated_request.question)
        if response.question_type != canonical_question_type or response.question_type == "unknown":
            response = response.model_copy(
                update={
                    "question_type": canonical_question_type,
                    "suggested_questions": _build_suggested_questions(
                        canonical_question_type,
                        response.matched_knowledge_points,
                    ),
                }
            )

        _persist_student_turn(session_store, history_store, response)

        return {
            "request": validated_request,
            "qa_output": agent.qa_output,
            "decision_output": agent.decision_output,
            "tool_trace": agent.tool_trace,
            "output": response,
            "events": list(conversation.state.events),
        }


# =====================================================================
# Prompt builders
# =====================================================================


def _build_context_turn_prompt(ctx: StudentTurnContext) -> str:
    """Build a user prompt for the new context-based path."""
    context_parts: list[str] = []
    if ctx.exact_source:
        context_parts.append(
            f"【精读内容】{ctx.exact_source.title or ctx.exact_source.source_id}: {_clean_text(ctx.exact_source.text, 400)}"
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
  "next_action": "resume|supplement_then_resume|reteach_slowly|trigger_game",
  "reason": "short Chinese explanation"
}}

If you decide next_action="trigger_game", call the game tool first.
Do not fabricate identifiers. If a value is unknown, use null.""".strip()


def _build_student_turn_prompt(request: StudentAgentRequest) -> str:
    """Legacy prompt that instructs the agent to use tools."""
    current_section_id = request.current_section_id or (
        request.session.current_section_id if request.session else None
    )
    current_page = (
        request.current_page
        if request.current_page is not None
        else (request.session.current_page if request.session else None)
    )
    current_script_block_id = request.current_script_block_id or (
        request.session.current_script_block_id if request.session else None
    )
    return f"""Student question: {request.question}

Course ID: {request.course_id}
Lesson ID: {request.lesson_id}
Session ID: {request.session_id}
Current section: {current_section_id}
Current page: {current_page}
Current script block: {current_script_block_id}

You must use the available tools before answering. Read the session, ground with search/retrieve, and consult memory if the question appears to be a follow-up.

When you have enough evidence, return JSON only with this shape:
{{
  "answer": "student-facing Chinese answer",
  "question_type": "definition|reasoning|procedure|example|comparison|summary|unknown",
  "understanding_level": "full|partial|none|null",
  "next_action": "resume|supplement_then_resume|reteach_slowly|trigger_game",
  "reason": "short Chinese explanation",
  "matched_section_id": null,
  "matched_page": null,
  "matched_script_block_id": null,
  "target_section_id": null,
  "target_page": null,
  "target_script_block_id": null
}}

If you decide `next_action="trigger_game"`, call the `game` tool first and then put the quiz text directly into `answer`.
When a game is triggered, `answer` should contain:
- the multiple-choice question
- the numbered options
- a short sentence asking the student to answer

Do not fabricate identifiers. If a value is unknown, use null.""".strip()


# =====================================================================
# LLM helpers
# =====================================================================


def _build_placeholder_llm() -> LLM:
    return LLM(model="gpt-4o-mini", api_key="test")


def _is_placeholder_llm(llm: LLM) -> bool:
    key = (llm.api_key.get_secret_value() if hasattr(llm, "api_key") and llm.api_key else "") or ""
    return key.lower() in PLACEHOLDER_API_KEY_MARKERS


def _llm_synthesize_answer(
    llm: LLM,
    question: str,
    question_type: StudentQuestionType,
    skill_name: str,
    exact_item: Optional[RetrievedContextItem],
    candidates: list[RetrievedContextItem],
    history_records: list[dict[str, Any]],
    fallback_answer: str,
) -> tuple[str, str]:
    if _is_placeholder_llm(llm):
        return fallback_answer, "fallback_rule"

    context_parts: list[str] = []
    if exact_item:
        context_parts.append(
            f"【精读内容】来源：{exact_item.title or exact_item.source_id}，内容：{_clean_text(exact_item.text, 400)}"
        )
    for i, cand in enumerate(candidates[:3]):
        if cand != exact_item:
            context_parts.append(
                f"【参考{i + 1}】来源：{cand.title or cand.source_id}，内容：{_clean_text(cand.text, 200)}"
            )

    history_snippet = ""
    if history_records:
        recent = history_records[-3:]
        history_snippet = "Recent QA history:\n" + "\n".join(
            f"- Q: {r.get('question', '')} A: {str(r.get('answer', ''))[:80]}" for r in recent
        )

    skill_style = SKILL_DISPLAY_NAMES.get(skill_name, skill_name)

    prompt = f"""You are a teaching assistant for a structured lesson platform. A student asked a question and you have retrieved lesson context to ground your answer.

Student Question: {question}
Question Type: {question_type}
Teaching Style: {skill_style}

Retrieved Context:
{chr(10).join(context_parts) if context_parts else "(No direct retrieval match found)"}

{history_snippet}

Instructions:
- Answer in Chinese (since the student asked in Chinese).
- Ground your answer in the retrieved context above.
- If there is no retrieval match, use the lesson summary context to give a reasonable answer.
- Keep your answer concise and focused (2-4 sentences for a direct answer, or a short paragraph for reasoning/explanation).
- Do NOT mention "based on the retrieval", "according to the context", or similar meta-commentary.
- Answer directly as a teaching assistant would.

Your answer:""".strip()

    messages = [Message(role="user", content=[TextContent(text=prompt)])]

    try:
        response = llm.completion(messages=messages, tools=None, add_security_risk_prediction=False)
        raw_text = " ".join(content_to_str(response.message.content))
        answer_text = raw_text.strip()
        if answer_text:
            return answer_text, "llm"
    except Exception:  # noqa: BLE001 - LLM may raise anything; log and fall back.
        logger.debug("Direct LLM answer call failed; falling back to rule-based answer.", exc_info=True)

    return fallback_answer, "fallback_rule"


def _decide_next_action_via_llm_ctx(
    ctx: StudentTurnContext,
    question: str,
    question_type: str,
    understanding_level: Optional[str],
    matched_section_id: Optional[str],
    matched_page: Optional[int],
    matched_script_block_id: Optional[str],
    history_records: list[dict[str, Any]],
    llm: LLM,
) -> dict[str, Any]:
    """LLM-based decision for the new context path."""
    rule_next_action = _decide_next_action_rule(question_type, understanding_level)
    if _is_placeholder_llm(llm):
        return {
            "next_action": rule_next_action,
            "reason": DECISION_REASONS[rule_next_action],
            "target_section_id": matched_section_id,
            "target_page": matched_page,
            "target_script_block_id": matched_script_block_id,
            "decision_source": "fallback_rule",
        }
    return _run_decision_llm_call(
        llm,
        question,
        question_type,
        understanding_level,
        matched_section_id,
        matched_page,
        matched_script_block_id,
        history_records,
        rule_next_action,
    )


def _decide_next_action_via_llm(
    request: StudentAgentRequest,
    question: str,
    question_type: StudentQuestionType,
    understanding_level: Optional[str],
    matched_section_id: Optional[str],
    matched_page: Optional[int],
    matched_script_block_id: Optional[str],
    history_records: list[dict[str, Any]],
    llm: LLM,
) -> dict[str, Any]:
    """LLM-based decision for the legacy path."""
    rule_next_action = _decide_next_action_rule(question_type, understanding_level)
    if _is_placeholder_llm(llm):
        return {
            "next_action": rule_next_action,
            "reason": DECISION_REASONS[rule_next_action],
            "target_section_id": matched_section_id,
            "target_page": matched_page,
            "target_script_block_id": matched_script_block_id,
            "decision_source": "fallback_rule",
        }
    return _run_decision_llm_call(
        llm,
        question,
        question_type,
        understanding_level,
        matched_section_id,
        matched_page,
        matched_script_block_id,
        history_records,
        rule_next_action,
    )


def _run_decision_llm_call(
    llm: LLM,
    question: str,
    question_type: str,
    understanding_level: Optional[str],
    matched_section_id: Optional[str],
    matched_page: Optional[int],
    matched_script_block_id: Optional[str],
    history_records: list[dict[str, Any]],
    rule_next_action: Optional[str],
) -> dict[str, Any]:
    history_snippet = ""
    if history_records:
        recent = history_records[-3:]
        history_snippet = "Recent QA history:\n" + "\n".join(
            f"- Q: {r.get('question', '')} A: {str(r.get('answer', ''))[:80]}" for r in recent
        )

    prompt = f"""Based on the student question and learning context, decide the next teaching action.

Question: {question}
Question Type: {question_type}
Understanding Level: {understanding_level or "unknown"}
Current Location: section={matched_section_id}, page={matched_page}, script_block={matched_script_block_id}

{history_snippet}

Allowed actions:
- resume: Continue to the next learning step naturally
- supplement_then_resume: First supplement with additional explanation, then continue
- reteach_slowly: Slow down and re-explain the current content
- trigger_game: Use an interactive game/quiz to reinforce understanding

Respond ONLY in this exact format (no other text):
ACTION: <one of the four allowed actions>
REASON: <brief Chinese explanation, 20-50 characters>
TARGET_SECTION: <section_id or null>
TARGET_PAGE: <page_number or null>
TARGET_SCRIPT_BLOCK: <script_block_id or null>""".strip()

    messages = [Message(role="user", content=[TextContent(text=prompt)])]

    try:
        response = llm.completion(messages=messages, tools=None, add_security_risk_prediction=False)
        raw_text = " ".join(content_to_str(response.message.content))
        return _parse_llm_decision_response(
            raw_text,
            fallback_next_action=rule_next_action,
            fallback_reason=DECISION_REASONS[rule_next_action],
            matched_section_id=matched_section_id,
            matched_page=matched_page,
            matched_script_block_id=matched_script_block_id,
        )
    except Exception:
        return {
            "next_action": rule_next_action,
            "reason": DECISION_REASONS[rule_next_action],
            "target_section_id": matched_section_id,
            "target_page": matched_page,
            "target_script_block_id": matched_script_block_id,
            "decision_source": "fallback_rule",
        }


def _parse_llm_decision_response(
    raw_response: str,
    fallback_next_action: Optional[str],
    fallback_reason: str,
    matched_section_id: Optional[str],
    matched_page: Optional[int],
    matched_script_block_id: Optional[str],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "next_action": fallback_next_action,
        "reason": fallback_reason,
        "target_section_id": matched_section_id,
        "target_page": matched_page,
        "target_script_block_id": matched_script_block_id,
        "decision_source": "llm",
    }

    action_match = re.search(r"ACTION:\s*(\w+)", raw_response, re.IGNORECASE)
    if action_match:
        action = action_match.group(1).strip().lower()
        if action in ALLOWED_NEXT_ACTIONS:
            result["next_action"] = action
            reason_match = re.search(r"REASON:\s*(.+?)(?=TARGET_|$)", raw_response, re.IGNORECASE | re.DOTALL)
            if reason_match:
                result["reason"] = reason_match.group(1).strip()[:200]

    section_match = re.search(r"TARGET_SECTION:\s*(\S+|null)", raw_response, re.IGNORECASE)
    if section_match:
        val = section_match.group(1).strip()
        if val.lower() != "null":
            result["target_section_id"] = val

    page_match = re.search(r"TARGET_PAGE:\s*(\d+|null)", raw_response, re.IGNORECASE)
    if page_match:
        val = page_match.group(1).strip()
        if val.lower() != "null":
            result["target_page"] = int(val)

    script_match = re.search(r"TARGET_SCRIPT_BLOCK:\s*(\S+|null)", raw_response, re.IGNORECASE)
    if script_match:
        val = script_match.group(1).strip()
        if val.lower() != "null":
            result["target_script_block_id"] = val

    return result


def _decide_next_action_rule(question_type: str, understanding_level: Optional[str]) -> Optional[str]:
    if understanding_level in {None, "none"}:
        return "reteach_slowly"
    if question_type in {"definition", "reasoning"}:
        return "supplement_then_resume"
    return "resume"


def _decide_next_action(
    question_type: StudentQuestionType, understanding_level: Optional[str]
) -> Optional[str]:
    """Public entry point for rule-based decision (used by tests)."""
    return _decide_next_action_rule(question_type, understanding_level)


# =====================================================================
# Helper functions
# =====================================================================


def _persist_student_turn(
    session_store: SessionStore,
    history_store: QAHistoryStore,
    response: StudentAgentResponse,
) -> None:
    if response.updated_session is not None:
        session_store.save(response.updated_session)
    if response.qa_record is not None:
        history_store.add(response.qa_record)


def _extract_tool_trace(events: list[Any]) -> list[dict[str, Any]]:
    actions_by_call_id: dict[str, dict[str, Any]] = {}
    trace: list[dict[str, Any]] = []
    for event in events:
        if isinstance(event, ActionEvent) and event.action is not None:
            actions_by_call_id[event.tool_call_id] = event.action.model_dump(mode="python")
        elif isinstance(event, ObservationEvent):
            trace.append(
                {
                    "tool": event.tool_name,
                    "action": actions_by_call_id.get(event.tool_call_id),
                    "is_error": event.observation.is_error,
                    "content": event.observation.text,
                }
            )
    return trace


def _collect_tool_state(events: list[Any]) -> dict[str, Any]:
    state: dict[str, Any] = {
        "session": None,
        "search_results": [],
        "search_total": 0,
        "exact_item": None,
        "history_records": [],
        "game": None,
    }
    for event in events:
        if not isinstance(event, ObservationEvent) or event.observation.is_error:
            continue
        observation = event.observation
        if event.tool_name == "session" and hasattr(observation, "session"):
            state["session"] = observation.session
        elif event.tool_name == "search" and hasattr(observation, "results"):
            state["search_results"] = list(observation.results)
            state["search_total"] = observation.total
        elif event.tool_name == "retrieve" and hasattr(observation, "retrieved_content"):
            state["exact_item"] = RetrievedContextItem(
                source=observation.source,
                source_id=observation.retrieved_content.get("source_id", ""),
                title=observation.retrieved_content.get("title", ""),
                text=observation.retrieved_content.get("text", ""),
                section_id=observation.retrieved_content.get("section_id"),
                page=observation.retrieved_content.get("page"),
                score=observation.retrieved_content.get("score"),
            )
        elif event.tool_name == "memory" and hasattr(observation, "records"):
            state["history_records"] = list(observation.records)
        elif event.tool_name == "game" and hasattr(observation, "prompt"):
            state["game"] = {
                "game_type": observation.game_type,
                "prompt": observation.prompt,
                "choices": list(observation.choices),
                "correct_index": observation.correct_index,
                "correct_choice": observation.correct_choice,
                "explanation": observation.explanation,
                "references": [ref.model_dump(mode="python") for ref in observation.references],
            }
    return state


def _get_latest_agent_message_text(events: list[Any]) -> str:
    for event in reversed(events):
        if isinstance(event, MessageEvent) and event.source == "agent":
            texts = content_to_str(event.llm_message.content)
            if texts:
                return " ".join(texts).strip()
    return ""


def _parse_agent_payload(message_text: str) -> dict[str, Any]:
    if not message_text:
        return {}
    cleaned = message_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


def _extract_game_payload(events: list[Any], tool_trace: list[dict[str, Any]]) -> dict[str, Any] | None:
    tool_state = _collect_tool_state(events)
    if tool_state.get("game") is not None:
        return tool_state["game"]
    for item in reversed(tool_trace):
        if item.get("tool") != "game":
            continue
        content = item.get("content") or ""
        lines = [line.strip() for line in str(content).splitlines() if line.strip()]
        if not lines:
            return None
        prompt = lines[0].replace("[GAME] ", "")
        choices = [line for line in lines[1:] if re.match(r"^\d+\.", line)]
        explanation = ""
        for line in lines:
            if line.startswith("Explanation:"):
                explanation = line.replace("Explanation:", "", 1).strip()
                break
        return {
            "game_type": "multiple_choice",
            "prompt": prompt,
            "choices": choices,
            "explanation": explanation,
        }
    return None


def _resolve_grounding(
    *,
    exact_item: Any,
    primary: Any,
    session: Any,
    request_section_id: Optional[str],
    request_page: Optional[int],
    request_script_block_id: Optional[str],
    payload_section_id: Optional[str] = None,
    payload_page: Optional[int] = None,
    payload_script_block_id: Optional[str] = None,
) -> tuple[Optional[str], Optional[int], Optional[str]]:
    """Compute ``(section_id, page, script_block_id)`` with priority cascade.

    Priority order::

        retrieved-exact > top-search-primary > session-cursor >
        request-default > LLM-payload (optional, last to avoid hallucination)

    All inputs are optional; returns ``(None, None, None)`` if nothing matches.
    The same cascade is applied independently to all three fields.
    """
    matched_section_id = (
        (exact_item.section_id if exact_item else None)
        or (primary.section_id if primary else None)
        or (session.current_section_id if session else None)
        or request_section_id
        or payload_section_id
    )
    matched_page = (
        (exact_item.page if exact_item else None)
        or (primary.page if primary else None)
        or (session.current_page if session else None)
        or request_page
        or payload_page
    )
    matched_script_block_id = (
        (exact_item.source_id if exact_item and exact_item.source == "script_block" else None)
        or (primary.source_id if primary and primary.source == "script_block" else None)
        or (session.current_script_block_id if session else None)
        or request_script_block_id
        or payload_script_block_id
    )
    return matched_section_id, matched_page, matched_script_block_id


def _normalize_understanding_level_local(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        value_lower = value.lower()
        if value_lower in {"full", "partial", "none"}:
            return value_lower
    return None


def _normalize_next_action_local(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        value_lower = value.lower()
        if value_lower in ALLOWED_NEXT_ACTIONS:
            return value_lower
    return None


def _build_base_session(request: StudentAgentRequest):
    from src.schemas import LearningSession

    if request.session is not None:
        return request.session.model_copy(deep=True)

    progress = request.progress
    return LearningSession(
        session_id=request.session_id,
        course_id=request.course_id,
        lesson_id=request.lesson_id,
        current_section_id=request.current_section_id or (progress.current_section_id if progress else None),
        current_page=request.current_page
        if request.current_page is not None
        else (progress.current_page if progress else None),
        current_script_block_id=request.current_script_block_id
        or (progress.current_script_block_id if progress else None),
        progress_percent=progress.progress_percent if progress else 0.0,
    )


def _seed_history_store(history_store: QAHistoryStore, request: StudentAgentRequest) -> None:
    for item in request.history_qa:
        record = QARecord(
            qa_record_id=item.qa_record_id or str(uuid4()),
            course_id=request.course_id,
            lesson_id=request.lesson_id,
            session_id=request.session_id,
            current_section_id=item.current_section_id,
            current_page=item.current_page,
            question=item.question,
            answer=item.answer,
            understanding_level=item.understanding_level,
            references=[],
        )
        history_store.add(record)


def _choose_primary_candidate(
    results: list[RetrievedContextItem],
    session,
    request: StudentAgentRequest,
) -> Optional[RetrievedContextItem]:
    if not results:
        return None
    preferred_script_block = session.current_script_block_id or request.current_script_block_id
    preferred_section = session.current_section_id or request.current_section_id
    preferred_page = session.current_page or request.current_page
    for item in results:
        if (
            preferred_script_block
            and item.source == "script_block"
            and item.source_id == preferred_script_block
        ):
            return item
    for item in results:
        if preferred_section and item.section_id == preferred_section:
            return item
    for item in results:
        if preferred_page is not None and item.page == preferred_page:
            return item
    return results[0]


def _build_retrieve_action(item: RetrievedContextItem) -> RetrieveAction:
    if item.source == "script_block":
        return RetrieveAction(script_block_id=item.source_id)
    if item.source == "section":
        return RetrieveAction(section_id=item.source_id)
    if item.source == "page":
        return RetrieveAction(page=item.page)
    return RetrieveAction(section_id=item.source_id)


def _observation_to_context_item(retrieve_obs) -> RetrievedContextItem:
    content = retrieve_obs.retrieved_content
    return RetrievedContextItem(
        source=retrieve_obs.source,
        source_id=content.get("source_id", ""),
        title=content.get("title", ""),
        text=content.get("text", ""),
        section_id=content.get("section_id"),
        page=content.get("page"),
        score=content.get("score"),
    )


def _build_references(
    candidates: list[RetrievedContextItem],
    exact_item: Optional[RetrievedContextItem],
) -> list[ReferenceItem]:
    references: list[ReferenceItem] = []
    seen: set[tuple[str, str]] = set()
    items = ([exact_item] if exact_item else []) + candidates[:3]
    for item in items:
        if item is None:
            continue
        key = (item.source, item.source_id)
        if key in seen:
            continue
        seen.add(key)
        references.append(
            ReferenceItem(
                source_type="script" if item.source == "script_block" else "lesson",
                source_name=item.title or item.source_id,
                section_id=item.section_id,
                script_block_id=item.source_id if item.source == "script_block" else None,
                page=item.page,
                snippet=_clean_text(item.text, 160),
                score=item.score,
            )
        )
    return references


def _build_fallback_reference(request: StudentAgentRequest) -> ReferenceItem:
    sc = request.structured_content
    if sc and sc.pages:
        first_page = sc.pages[0]
        return ReferenceItem(
            source_type="fallback",
            source_name=first_page.title or "lesson_summary",
            section_id=first_page.section_id or request.current_section_id,
            page=first_page.page or request.current_page,
            snippet=_clean_text(first_page.summary or (sc.lesson_summary if sc else ""), 160),
        )
    return ReferenceItem(
        source_type="fallback",
        source_name="lesson_summary",
        section_id=request.current_section_id,
        page=request.current_page,
        snippet=_clean_text(sc.lesson_summary if sc else "", 160),
    )


def _build_fallback_reference_from_context(ctx: StudentTurnContext) -> ReferenceItem:
    sc = ctx.structured_content
    if sc and sc.pages:
        first_page = sc.pages[0]
        return ReferenceItem(
            source_type="fallback",
            source_name=first_page.title or "lesson_summary",
            section_id=first_page.section_id or ctx.current_section_id,
            page=first_page.page or ctx.current_page,
            snippet=_clean_text(first_page.summary or sc.lesson_summary, 160),
        )
    return ReferenceItem(
        source_type="fallback",
        source_name="lesson_summary",
        section_id=ctx.current_section_id,
        page=ctx.current_page,
        snippet=_clean_text(sc.lesson_summary if sc else "", 160),
    )


def _infer_understanding_level(
    question_type: str,
    exact_item: Optional[RetrievedContextItem],
    search_total: int,
    *,
    has_lesson_context: bool,
) -> str:
    if exact_item is None and search_total == 0:
        if has_lesson_context and question_type != "unknown":
            return "partial"
        return "none"
    if question_type in {"definition", "reasoning"}:
        return "partial"
    return "full"


def _compose_answer(
    request: StudentAgentRequest,
    *,
    question: str,
    question_type: str,
    skill_name: str,
    exact_item: Optional[RetrievedContextItem],
    candidates: list[RetrievedContextItem],
    history_records: list[dict[str, Any]],
) -> str:
    sc = request.structured_content
    if exact_item is None and not candidates:
        summary = sc.lesson_summary.strip() if sc else ""
        if summary:
            return f"我先根据当前课时内容给出概括：{summary}"
        return "我暂时没有拿到足够的课时上下文，请先确认教师侧结构化内容是否已经生成。"
    return _format_answer_body(question, question_type, skill_name, exact_item, candidates, history_records)


def _compose_answer_from_context(
    ctx: StudentTurnContext,
    *,
    question: str,
    question_type: str,
    skill_name: str,
    exact_item: Optional[RetrievedContextItem],
    candidates: list[RetrievedContextItem],
    history_records: list[dict[str, Any]],
) -> str:
    sc = ctx.structured_content
    if exact_item is None and not candidates:
        summary = sc.lesson_summary.strip() if sc else ""
        if summary:
            return f"我先根据当前课时内容给出概括：{summary}"
        return "我暂时没有拿到足够的课时上下文，请先确认教师侧结构化内容是否已经生成。"
    return _format_answer_body(question, question_type, skill_name, exact_item, candidates, history_records)


def _format_answer_body(
    question: str,
    question_type: str,
    skill_name: str,
    exact_item: Optional[RetrievedContextItem],
    candidates: list[RetrievedContextItem],
    history_records: list[dict[str, Any]],
) -> str:
    primary = exact_item or candidates[0]
    style = SKILL_DISPLAY_NAMES.get(skill_name, skill_name)
    topic = primary.title or "当前知识点"
    snippet = _clean_text(primary.text, 220)
    answer_parts = [
        f"先用{style}回答你的问题。",
        f"围绕「{topic}」，当前课时内容显示：{snippet}",
    ]
    related_titles = [item.title for item in candidates[:3] if item.title and item.title != topic]
    if related_titles:
        answer_parts.append(f"你还可以结合 {', '.join(dict.fromkeys(related_titles))} 一起理解。")
    if history_records:
        last_question = history_records[-1].get("question", "").strip()
        if last_question and last_question != question:
            answer_parts.append(f"这和你之前问的「{last_question}」是连续的学习问题。")
    strategy_hint = _extract_skill_hint(skill_name)
    if strategy_hint:
        answer_parts.append(strategy_hint)
    return " ".join(part for part in answer_parts if part).strip()


def _extract_skill_hint(skill_name: str) -> str:
    skill_content = get_skill_content(skill_name)
    for line in skill_content.splitlines():
        stripped = line.strip(" #-*")
        if stripped:
            return f"本轮采用的讲解策略重点是：{_clean_text(stripped, 80)}。"
    return ""


def _estimate_progress(request: StudentAgentRequest, next_action: Optional[str]) -> float:
    current = 0.0
    if request.progress is not None:
        current = request.progress.progress_percent
    elif request.session is not None:
        current = request.session.progress_percent
    delta_map: dict[Optional[str], float] = {
        "resume": 5.0,
        "supplement_then_resume": 3.0,
        "reteach_slowly": 1.0,
        "trigger_game": 2.0,
        None: 0.0,
    }
    return min(100.0, max(0.0, current + delta_map[next_action]))


def _build_suggested_questions(
    question_type: StudentQuestionType,
    matched_knowledge_points: list[Any],
) -> list[str]:
    topic = matched_knowledge_points[0].knowledge_point if matched_knowledge_points else "这个知识点"
    suggestions: dict[str, list[str]] = {
        "definition": [f"{topic}为什么重要？", f"{topic}可以怎么应用？"],
        "reasoning": [f"{topic}的原因还能再展开吗？", f"{topic}能举个例子吗？"],
        "procedure": [f"{topic}每一步为什么这样做？", f"{topic}有哪些常见错误？"],
        "example": [f"{topic}还有别的例子吗？", f"{topic}和相近概念有什么区别？"],
        "comparison": [f"{topic}分别适合什么场景？", f"{topic}的核心差异是什么？"],
        "summary": [f"{topic}里最关键的点是什么？", f"我怎么检查自己是否真的理解了 {topic}？"],
        "unknown": [f"{topic}对应课件的哪一部分？", f"{topic}能换一种方式解释吗？"],
    }
    return suggestions.get(question_type, suggestions["unknown"])


def _build_agent_message(answer: str, next_action: Optional[str], session) -> str:
    suffix = DECISION_REASONS[next_action]
    location_bits: list[str] = []
    if session is not None:
        if session.current_section_id:
            location_bits.append(f"section={session.current_section_id}")
        if session.current_page is not None:
            location_bits.append(f"page={session.current_page}")
    location = f" 当前定位：{', '.join(location_bits)}。" if location_bits else ""
    return f"{answer}\n\n下一步建议：{next_action or 'none'}。{suffix}{location}"


def _clean_text(text: str, limit: int) -> str:
    compact = " ".join((text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _get_latest_user_question(conversation) -> str:
    for event in reversed(list(conversation.state.events)):
        if isinstance(event, MessageEvent) and event.source == "user":
            texts = [item.text for item in event.llm_message.content if isinstance(item, TextContent)]
            if texts:
                return " ".join(texts).strip()
    return ""
