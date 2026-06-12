from typing import Literal, Optional

from pydantic import Field

from .base import BaseRequest, BaseResponse
from .common import NextAction, UnderstandingLevel


class DecisionInput(BaseRequest):
    course_id: Optional[str] = Field(default=None, description="课程 ID")
    lesson_id: str = Field(..., description="课时 ID")
    session_id: str = Field(..., description="学习会话 ID")
    current_section_id: Optional[str] = Field(default=None, description="当前章节 ID")
    current_page: Optional[int] = Field(default=None, description="当前页码")
    current_script_block_id: Optional[str] = Field(default=None, description="当前讲稿块 ID")
    question: str = Field(..., description="学生问题")
    answer: str = Field(..., description="QA 模块回答")
    understanding_level: UnderstandingLevel = Field(..., description="理解程度")


class DecisionOutput(BaseResponse):
    course_id: Optional[str] = Field(default=None, description="课程 ID")
    lesson_id: Optional[str] = Field(default=None, description="课时 ID")
    session_id: Optional[str] = Field(default=None, description="学习会话 ID")
    next_action: Optional[NextAction] = Field(default=None, description="下一步动作")
    reason: str = Field(default="", description="动作判断原因")
    target_section_id: Optional[str] = Field(default=None, description="建议跳转或续接的章节 ID")
    target_page: Optional[int] = Field(default=None, description="建议跳转或续接的页码")
    target_script_block_id: Optional[str] = Field(default=None, description="建议续接的讲稿块 ID")
    supplement_content: str = Field(default="", description="需要补充讲解时的附加内容")
    game_trigger: Optional[Literal["quiz", "flashcard", "mini_game"]] = Field(
        default=None,
        description="若触发互动，则给出互动类型",
    )
