from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Optional

from pydantic import Field, model_validator

from .base import BaseRequest, BaseResponse, SchemaModel
from .common import (
    LearningProgress,
    LearningSession,
    NextAction,
    QAHistoryItem,
    QARecord,
    ReferenceItem,
    StructuredLessonContent,
    UnderstandingLevel,
)
from .generate_schemas import LessonScript

if TYPE_CHECKING:
    from .student_turn_context import StudentTurnContext

StudentQuestionType = Literal[
    "definition",
    "reasoning",
    "procedure",
    "example",
    "comparison",
    "summary",
    "chitchat",
    "unknown",
]

NarrationLevel = Literal["A", "B", "C", "D"]


class KnowledgePointMatch(SchemaModel):
    knowledge_point: str = Field(..., description="Matched knowledge point name")
    score: Optional[float] = Field(default=None, description="Retrieval or routing confidence score")
    source_section_ids: list[str] = Field(
        default_factory=list,
        description="Related teaching section identifiers",
    )
    source_pages: list[int] = Field(
        default_factory=list,
        description="Related teaching page numbers",
    )
    source_script_block_ids: list[str] = Field(
        default_factory=list,
        description="Related lesson script block identifiers",
    )
    rationale: str = Field(
        default="", description="Short explanation of why this knowledge point was matched"
    )


class RetrievedContextItem(SchemaModel):
    source: Literal["page", "section", "script_block"] = Field(
        ...,
        description="Retrieved context source type",
    )
    source_id: str = Field(..., description="Unique identifier of the retrieved source object")
    title: str = Field(default="", description="Human-readable title of the retrieved source")
    text: str = Field(default="", description="Retrieved text content passed to the LLM")
    section_id: Optional[str] = Field(default=None, description="Owning teaching section identifier")
    page: Optional[int] = Field(default=None, description="Owning teaching page number")
    score: Optional[float] = Field(default=None, description="Retrieval relevance score when available")


class StudentAgentRequest(BaseRequest):
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: str = Field(..., description="Lesson identifier")
    session_id: str = Field(..., description="Learning session identifier")
    question: str = Field(..., description="Student utterance for the current turn")
    structured_content: Optional[StructuredLessonContent] = Field(
        default=None,
        description="Structured lesson content (optional -- new path uses turn_context instead)",
    )
    lesson_script: Optional[LessonScript] = Field(
        default=None,
        description="Lesson script generated from the teacher pipeline",
    )
    turn_context: Optional[StudentTurnContext] = Field(
        default=None,
        description="Pre-assembled turn context from the backend service layer",
    )
    session: Optional[LearningSession] = Field(
        default=None,
        description="Current learning session snapshot",
    )
    progress: Optional[LearningProgress] = Field(
        default=None,
        description="Current learning progress snapshot",
    )
    history_qa: list[QAHistoryItem] = Field(
        default_factory=list,
        description="Recent QA history already visible to the agent",
    )
    current_section_id: Optional[str] = Field(
        default=None,
        description="Current teaching section identifier for this turn",
    )
    current_page: Optional[int] = Field(
        default=None,
        description="Current teaching page number for this turn",
    )
    current_script_block_id: Optional[str] = Field(
        default=None,
        description="Current lesson script block identifier for this turn",
    )
    student_profile: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional student profile or preference signals",
    )

    @model_validator(mode="after")
    def normalize_and_validate(self) -> StudentAgentRequest:
        sc = self.structured_content

        if self.course_id is None:
            self.course_id = (
                (sc.course_id if sc else None)
                or (self.session.course_id if self.session else None)
                or (self.progress.course_id if self.progress else None)
                or (self.turn_context.course_id if self.turn_context else None)
            )

        if self.current_section_id is None:
            self.current_section_id = (self.session.current_section_id if self.session else None) or (
                self.progress.current_section_id if self.progress else None
            )

        if self.current_page is None:
            self.current_page = (self.session.current_page if self.session else None) or (
                self.progress.current_page if self.progress else None
            )

        if self.current_script_block_id is None:
            self.current_script_block_id = (
                self.session.current_script_block_id if self.session else None
            ) or (self.progress.current_script_block_id if self.progress else None)

        if sc is not None and sc.lesson_id != self.lesson_id:
            raise ValueError("structured_content.lesson_id must match StudentAgentRequest.lesson_id")

        if self.lesson_script and self.lesson_script.metadata.get("lesson_id") not in (None, self.lesson_id):
            raise ValueError(
                "lesson_script.metadata.lesson_id must match StudentAgentRequest.lesson_id when present"
            )

        if self.session:
            if self.session.lesson_id != self.lesson_id:
                raise ValueError("session.lesson_id must match StudentAgentRequest.lesson_id")
            if self.session.session_id != self.session_id:
                raise ValueError("session.session_id must match StudentAgentRequest.session_id")

        if self.progress:
            if self.progress.lesson_id != self.lesson_id:
                raise ValueError("progress.lesson_id must match StudentAgentRequest.lesson_id")
            if self.progress.session_id != self.session_id:
                raise ValueError("progress.session_id must match StudentAgentRequest.session_id")

        return self


class StudentAgentResponse(BaseResponse):
    course_id: Optional[str] = Field(default=None, description="Course identifier")
    lesson_id: str = Field(..., description="Lesson identifier")
    session_id: str = Field(..., description="Learning session identifier")
    answer: str = Field(default="", description="Student-facing answer for this turn")
    references: list[ReferenceItem] = Field(
        default_factory=list, description="Grounding references for the answer"
    )
    question_type: StudentQuestionType = Field(
        default="unknown",
        description="Question routing category chosen for this turn",
    )
    understanding_level: Optional[UnderstandingLevel] = Field(
        default=None,
        description="Estimated student understanding level after this turn",
    )
    recommended_narration_level: Optional[NarrationLevel] = Field(
        default=None,
        description="Recommended narration detail level for the next explanation",
    )
    next_action: Optional[NextAction] = Field(
        default=None,
        description="Recommended next teaching action after the answer",
    )
    reason: str = Field(default="", description="Short explanation for the chosen next action")
    matched_knowledge_points: list[KnowledgePointMatch] = Field(
        default_factory=list,
        description="Knowledge-point level matches used for retrieval or routing",
    )
    matched_section_id: Optional[str] = Field(
        default=None,
        description="Primary section matched for the answer",
    )
    matched_page: Optional[int] = Field(
        default=None,
        description="Primary page matched for the answer",
    )
    matched_script_block_id: Optional[str] = Field(
        default=None,
        description="Primary script block matched for the answer",
    )
    target_section_id: Optional[str] = Field(
        default=None,
        description="Recommended next teaching section identifier",
    )
    target_page: Optional[int] = Field(
        default=None,
        description="Recommended next teaching page number",
    )
    target_script_block_id: Optional[str] = Field(
        default=None,
        description="Recommended next script block identifier",
    )
    suggested_questions: list[str] = Field(
        default_factory=list,
        description="Optional follow-up questions for the student",
    )
    updated_session: Optional[LearningSession] = Field(
        default=None,
        description="Session snapshot after this turn",
    )
    updated_progress: Optional[LearningProgress] = Field(
        default=None,
        description="Progress snapshot after this turn",
    )
    qa_record: Optional[QARecord] = Field(
        default=None,
        description="Persistable QA record for this turn",
    )

    @model_validator(mode="after")
    def validate_related_outputs(self) -> StudentAgentResponse:
        if self.updated_session:
            if self.updated_session.lesson_id != self.lesson_id:
                raise ValueError("updated_session.lesson_id must match StudentAgentResponse.lesson_id")
            if self.updated_session.session_id != self.session_id:
                raise ValueError("updated_session.session_id must match StudentAgentResponse.session_id")

        if self.updated_progress:
            if self.updated_progress.lesson_id != self.lesson_id:
                raise ValueError("updated_progress.lesson_id must match StudentAgentResponse.lesson_id")
            if self.updated_progress.session_id != self.session_id:
                raise ValueError("updated_progress.session_id must match StudentAgentResponse.session_id")

        if self.qa_record:
            if self.qa_record.lesson_id != self.lesson_id:
                raise ValueError("qa_record.lesson_id must match StudentAgentResponse.lesson_id")
            if self.qa_record.session_id != self.session_id:
                raise ValueError("qa_record.session_id must match StudentAgentResponse.session_id")

        return self
