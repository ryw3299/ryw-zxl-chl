"""OpenHands adapter for the student multiple-choice game tool."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, ClassVar

from openhands.sdk.llm import TextContent
from openhands.sdk.tool import Action, Observation, ToolAnnotations, ToolDefinition, ToolExecutor
from openhands.sdk.tool.registry import register_tool
from pydantic import Field

from src.schemas import ReferenceItem, StructuredLessonContent
from src.tools.game import GameAction as BusinessGameAction
from src.tools.game import GameObservation as BusinessGameObservation
from src.tools.game import GameTool as BusinessGameTool


class GameAction(Action):
    mode: str = Field(
        default="multiple_choice", description="Game mode. Current supported value: multiple_choice"
    )
    question: str = Field(description="Student question or current teaching topic")
    lesson_id: str = Field(description="Lesson identifier")
    session_id: str = Field(description="Session identifier")
    section_id: str | None = Field(default=None, description="Preferred section")
    page: int | None = Field(default=None, description="Preferred page")


class GameObservation(Observation):
    game_type: str = Field(default="multiple_choice")
    prompt: str = Field(default="")
    choices: list[str] = Field(default_factory=list)
    correct_index: int = Field(default=0)
    correct_choice: str = Field(default="")
    explanation: str = Field(default="")
    references: list[ReferenceItem] = Field(default_factory=list)


class GameExecutor(ToolExecutor[GameAction, GameObservation]):
    def __init__(self, business_tool: BusinessGameTool):
        self._business_tool = business_tool

    def __call__(self, action: GameAction, conversation: Any | None = None) -> GameObservation:
        try:
            result: BusinessGameObservation = self._business_tool.run(
                BusinessGameAction(
                    mode=action.mode,
                    question=action.question,
                    lesson_id=action.lesson_id,
                    session_id=action.session_id,
                    section_id=action.section_id,
                    page=action.page,
                )
            )
            choice_lines = [f"{idx + 1}. {choice}" for idx, choice in enumerate(result.choices)]
            content_text = "\n".join(
                [
                    f"[GAME] {result.prompt}",
                    *choice_lines,
                    f"Correct choice index: {result.correct_index + 1}",
                    f"Explanation: {result.explanation}",
                ]
            )
            return GameObservation(
                game_type=result.game_type,
                prompt=result.prompt,
                choices=result.choices,
                correct_index=result.correct_index,
                correct_choice=result.correct_choice,
                explanation=result.explanation,
                references=result.references,
                content=[TextContent(text=content_text)],
            )
        except ValueError as exc:
            return GameObservation(
                game_type="multiple_choice",
                prompt="",
                choices=[],
                correct_index=0,
                correct_choice="",
                explanation="",
                references=[],
                is_error=True,
                content=[TextContent(text=f"Error: {exc}")],
            )


GAME_TOOL_DESCRIPTION = """Generate one grounded multiple-choice quiz from the current lesson.

Use this tool when you want to switch into a lightweight interactive teaching mode.
It returns:
- prompt
- choices
- correct_index
- correct_choice
- explanation
- references

Current supported mode:
- multiple_choice
"""


class GameOpenHandsTool(ToolDefinition[GameAction, GameObservation]):
    name: ClassVar[str] = "game"

    @classmethod
    def create(
        cls,
        conv_state: Any = None,
        **params: Any,
    ) -> Sequence[GameOpenHandsTool]:
        structured_content: StructuredLessonContent | None = params.get("structured_content")
        if structured_content is None:
            raise ValueError("GameOpenHandsTool.create() requires 'structured_content' to be injected.")

        business_tool = BusinessGameTool(structured_content=structured_content)
        executor = GameExecutor(business_tool=business_tool)
        return [
            cls(
                action_type=GameAction,
                observation_type=GameObservation,
                description=GAME_TOOL_DESCRIPTION,
                annotations=ToolAnnotations(
                    title="game",
                    readOnlyHint=True,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
                executor=executor,
            )
        ]


register_tool("game", GameOpenHandsTool)
