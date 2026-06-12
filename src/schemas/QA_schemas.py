from typing import Optional

from pydantic import Field

from .base import BaseRequest, BaseResponse
from .common import QAHistoryItem, ReferenceItem, UnderstandingLevel


class QAInput(BaseRequest):
    course_id: Optional[str] = Field(default=None, description="课程 ID")
    lesson_id: str = Field(..., description="课时 ID")
    session_id: str = Field(..., description="学习会话 ID")
    current_section_id: Optional[str] = Field(default=None, description="当前章节 ID")
    current_page: Optional[int] = Field(default=None, description="当前页码")
    current_script_block_id: Optional[str] = Field(default=None, description="当前讲稿块 ID")
    question: str = Field(..., description="学生当前问题")
    history_qa: list[QAHistoryItem] = Field(default_factory=list, description="历史问答")


class QAOutput(BaseResponse):
    course_id: Optional[str] = Field(default=None, description="课程 ID")
    lesson_id: Optional[str] = Field(default=None, description="课时 ID")
    session_id: Optional[str] = Field(default=None, description="学习会话 ID")
    answer: str = Field(default="", description="回答内容")
    references: list[ReferenceItem] = Field(default_factory=list, description="参考来源")
    understanding_level: Optional[UnderstandingLevel] = Field(default=None, description="理解程度判断")
    matched_section_id: Optional[str] = Field(default=None, description="本次回答命中的章节 ID")
    matched_page: Optional[int] = Field(default=None, description="本次回答命中的页码")
    suggested_questions: list[str] = Field(default_factory=list, description="建议学生继续追问的问题")
