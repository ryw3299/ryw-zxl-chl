"""Minimal game tool for generating grounded multiple-choice questions."""

from __future__ import annotations

import re
from typing import Optional

from pydantic import Field

from src.schemas import ReferenceItem, StructuredLessonContent
from src.schemas.base import SchemaModel


class GameAction(SchemaModel):
    """Input schema for generating a lightweight in-lesson quiz."""

    mode: str = Field(
        default="multiple_choice", description="Game mode. Current supported value: multiple_choice"
    )
    question: str = Field(..., description="Student question or current teaching topic")
    lesson_id: str = Field(..., description="Lesson identifier")
    session_id: str = Field(..., description="Session identifier")
    section_id: Optional[str] = Field(default=None, description="Preferred section for grounding")
    page: Optional[int] = Field(default=None, description="Preferred page for grounding")


class GameObservation(SchemaModel):
    """Structured quiz payload returned by the game tool."""

    game_type: str = Field(default="multiple_choice")
    prompt: str = Field(default="")
    choices: list[str] = Field(default_factory=list)
    correct_index: int = Field(default=0)
    correct_choice: str = Field(default="")
    explanation: str = Field(default="")
    references: list[ReferenceItem] = Field(default_factory=list)


class GameTool:
    """Generate one grounded multiple-choice quiz from structured lesson content."""

    def __init__(self, structured_content: StructuredLessonContent):
        self.structured_content = structured_content

    def run(self, action: GameAction) -> GameObservation:
        if action.mode != "multiple_choice":
            raise ValueError("only mode='multiple_choice' is supported")

        if action.lesson_id != self.structured_content.lesson_id:
            raise ValueError("action.lesson_id must match structured_content.lesson_id")

        selected_page = self._select_page(action)
        if selected_page is None:
            raise ValueError("unable to generate a quiz because no matching lesson content was found")

        topic = (
            (selected_page.knowledge_points or selected_page.key_points or [selected_page.title])[0]
            if (selected_page.knowledge_points or selected_page.key_points or [selected_page.title])  # noqa: SIM222 - explicit fallback list keeps the conditional symmetric
            else "当前知识点"
        )
        correct_choice = self._build_correct_choice(
            selected_page.content or selected_page.summary or selected_page.title
        )
        distractors = self._build_distractors(selected_page.page_id, correct_choice)
        choices = [correct_choice, *distractors[:3]]

        prompt = f"关于“{topic}”，下列哪一项最符合本课时内容？"
        explanation = selected_page.summary or self._build_correct_choice(selected_page.content)
        references = [
            ReferenceItem(
                source_type="lesson",
                source_name=selected_page.title or selected_page.page_id or f"page-{selected_page.page}",
                section_id=selected_page.section_id,
                page=selected_page.page,
                snippet=self._truncate(selected_page.content or selected_page.summary),
            )
        ]

        return GameObservation(
            game_type="multiple_choice",
            prompt=prompt,
            choices=choices,
            correct_index=0,
            correct_choice=correct_choice,
            explanation=explanation,
            references=references,
        )

    def _select_page(self, action: GameAction):
        if action.page is not None:
            for page in self.structured_content.pages:
                if page.page == action.page:
                    return page

        if action.section_id:
            for page in self.structured_content.pages:
                if page.section_id == action.section_id:
                    return page

        normalized_question = (action.question or "").strip().lower()
        if normalized_question:
            for page in self.structured_content.pages:
                haystacks = [
                    page.title,
                    page.content,
                    page.summary,
                    " ".join(page.knowledge_points),
                    " ".join(page.key_points),
                ]
                if any(normalized_question in (item or "").lower() for item in haystacks):
                    return page

                question_terms = [term for term in re.split(r"\W+", normalized_question) if term]
                if any(
                    term in (page.content or "").lower()
                    or term in (page.title or "").lower()
                    or term in " ".join(page.knowledge_points).lower()
                    for term in question_terms
                ):
                    return page

        return self.structured_content.pages[0] if self.structured_content.pages else None

    def _build_correct_choice(self, text: str) -> str:
        compact = self._truncate(text, limit=48)
        return compact or "它是当前课时中的核心概念。"

    def _build_distractors(self, selected_page_id: Optional[str], correct_choice: str) -> list[str]:
        distractors: list[str] = []
        for page in self.structured_content.pages:
            if page.page_id == selected_page_id:
                continue
            candidate = self._truncate(page.summary or page.title or page.content, limit=48)
            if candidate and candidate != correct_choice and candidate not in distractors:
                distractors.append(candidate)

        generic = [
            "它只表示课件的标题信息。",
            "它与当前课时无关，只是历史背景补充。",
            "它主要描述作业提交流程，而不是知识内容。",
        ]
        for item in generic:
            if item != correct_choice and item not in distractors:
                distractors.append(item)
        return distractors

    @staticmethod
    def _truncate(text: str, limit: int = 80) -> str:
        compact = " ".join((text or "").split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 3] + "..."
