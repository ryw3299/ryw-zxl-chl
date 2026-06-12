"""Routers for the 学习进度智能适配模块 (/api/v1/progress/*)."""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.deps import generate_request_id
from src.api.models.database import get_db
from src.api.response_models import (
    AdjustData,
    ApiResponse,
    ErrorResponse,
    TrackData,
)
from src.api.services import progress_service

router = APIRouter(prefix="/progress", tags=["学习进度"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "参数错误"},
    404: {"model": ErrorResponse, "description": "资源不存在"},
}


# ── request schemas ──────────────────────────────────────────────────


class TrackRequest(BaseModel):
    """学习进度追踪请求"""

    schoolId: str = Field(..., description="学校 ID", example="sch10001")
    userId: str = Field(..., description="学生学号/用户 ID", example="stu20001")
    courseId: str = Field(..., description="课程 ID", example="cou30001")
    lessonId: str = Field(..., description="智课 ID", example="lesson20240520001")
    currentSectionId: str = Field(..., description="当前学习章节 ID", example="sec002")
    progressPercent: float = Field(..., description="章节学习进度（0-100）", example=60.5)
    lastOperateTime: str = Field(..., description="最后操作时间", example="2024-05-20 10:10:00")
    qaRecordId: Optional[str] = Field(
        None,
        description="最近问答记录 ID（如有）",
        example="ans20240520001",
    )
    enc: str = Field("", description="签名信息")
    time: str = Field("", description="当前时间")


class AdjustRequest(BaseModel):
    """学习节奏调整请求"""

    userId: str = Field(..., description="学生学号/用户 ID", example="stu20001")
    lessonId: str = Field(..., description="智课 ID", example="lesson20240520001")
    currentSectionId: str = Field(..., description="当前章节 ID", example="sec002")
    understandingLevel: str = Field(
        ...,
        description="理解程度（来自问答结果）：none（未理解）、partial（部分理解）、full（完全理解）",
        example="partial",
    )
    qaRecordId: str = Field(..., description="问答记录 ID", example="ans20240520001")
    enc: str = Field("", description="签名信息")
    time: str = Field("", description="当前时间")


# ── routes ────────────────────────────────────────────────────────────


@router.post(
    "/track",
    response_model=ApiResponse[TrackData],
    responses=_ERROR_RESPONSES,
    summary="学习进度追踪",
    description="记录学生学习进度、问答交互记录，为适配调整提供数据支撑。",
)
def track_progress(body: TrackRequest, db: Session = Depends(get_db)):
    result = progress_service.track_progress(
        db,
        school_id=body.schoolId,
        user_id=body.userId,
        course_id=body.courseId,
        lesson_id=body.lessonId,
        current_section_id=body.currentSectionId,
        progress_percent=body.progressPercent,
        last_operate_time=body.lastOperateTime,
        qa_record_id=body.qaRecordId,
    )

    return {
        "code": 200,
        "msg": "进度追踪成功",
        "data": result,
        "requestId": generate_request_id(),
    }


@router.post(
    "/adjust",
    response_model=ApiResponse[AdjustData],
    responses=_ERROR_RESPONSES,
    summary="学习节奏调整",
    description="基于学生理解程度与学习进度，调整后续讲授节奏。"
    "支持补充讲解（supplement）、加速（accelerate）、正常（normal）三种调整模式。",
)
def adjust_pace(body: AdjustRequest, db: Session = Depends(get_db)):
    result = progress_service.adjust_pace(
        db,
        user_id=body.userId,
        lesson_id=body.lessonId,
        current_section_id=body.currentSectionId,
        understanding_level=body.understandingLevel,
        qa_record_id=body.qaRecordId,
    )

    return {
        "code": 200,
        "msg": "节奏调整成功",
        "data": result,
        "requestId": generate_request_id(),
    }
