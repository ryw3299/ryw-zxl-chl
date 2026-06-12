"""Lightweight context object assembled by the backend before invoking the student agent.

The ``StudentTurnContext`` replaces the previous pattern where the full
``structured_content`` was threaded through every tool.  The backend
(via ``context_builder``) populates this object with pre-retrieved chunks,
session state, and recent conversation turns so the agent only needs to
generate an answer and decide the next action.
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import Field

from .base import SchemaModel
from .common import LearningSession, StructuredLessonContent
from .generate_schemas import LessonScript
from .student_schemas import RetrievedContextItem


class StudentTurnContext(SchemaModel):
    session_id: str = Field(..., description="Learning session identifier")
    user_id: Optional[str] = Field(default=None, description="Student user identifier")
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: str = Field(..., description="Lesson identifier")
    question: str = Field(..., description="Student question for this turn")
    question_type: str = Field(default="unknown", description="Classified question type")

    current_section_id: Optional[str] = Field(default=None, description="Current section identifier")
    current_page: Optional[int] = Field(default=None, description="Current page number")
    current_script_block_id: Optional[str] = Field(
        default=None, description="Current script block identifier"
    )

    session_snapshot: Optional[LearningSession] = Field(
        default=None,
        description="Session state read from the backend before agent invocation",
    )
    recent_turns: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Last N QA turns from conversation history",
    )
    retrieved_chunks: list[RetrievedContextItem] = Field(
        default_factory=list,
        description="Top-k retrieval results from pre-RAG stage",
    )
    exact_source: Optional[RetrievedContextItem] = Field(
        default=None,
        description="Best-matching exact source from retrieval",
    )

    structured_content: Optional[StructuredLessonContent] = Field(
        default=None,
        description="Structured lesson content (cached internally, not passed per-request)",
    )
    lesson_script: Optional[LessonScript] = Field(
        default=None,
        description="Lesson script (cached internally, not passed per-request)",
    )
