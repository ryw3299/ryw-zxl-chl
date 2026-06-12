"""Routers for platform integration (/api/v1/platform/*)."""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.deps import generate_request_id
from src.api.models.database import get_db
from src.api.response_models import (
    ApiResponse,
    ErrorResponse,
    SyncCourseData,
    SyncUserData,
)
from src.api.services import platform_service

router = APIRouter(prefix="/platform", tags=["平台对接"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "参数错误"},
}


# ── request schemas ──────────────────────────────────────────────────


class SyncCourseRequest(BaseModel):
    """课程信息同步请求"""

    platformId: str = Field(..., description="外部平台 ID（对接时分配）", example="plat001")
    courseInfo: dict = Field(
        ...,
        description="课程信息",
        example={
            "courseId": "plat_cou001",
            "courseName": "材料力学（上册）",
            "schoolId": "sch10001",
            "schoolName": "某某大学",
            "teacherInfo": [{"teacherId": "plat_tea001", "teacherName": "张教授"}],
            "term": "20242",
            "credit": 3.0,
            "period": 48,
            "courseCover": "http://xxx.com/course/cover/001.jpg",
        },
    )
    enc: str = Field("", description="签名信息")
    time: str = Field("", description="当前时间")


class SyncUserRequest(BaseModel):
    """用户信息同步请求"""

    platformId: str = Field(..., description="外部平台 ID", example="plat001")
    userInfo: dict = Field(
        ...,
        description="用户信息",
        example={
            "userId": "plat_stu001",
            "userName": "李四",
            "role": "student",
            "schoolId": "sch10001",
            "relatedCourseIds": ["plat_cou001"],
            "contactInfo": {
                "phone": "13800138000",
                "email": "lisi@xxx.com",
            },
        },
    )
    enc: str = Field("", description="签名信息")
    time: str = Field("", description="当前时间")


# ── routes ────────────────────────────────────────────────────────────


@router.post(
    "/syncCourse",
    response_model=ApiResponse[SyncCourseData],
    responses=_ERROR_RESPONSES,
    summary="课程信息同步",
    description="与外部教育平台同步课程基础信息，支持智课关联课程体系。",
)
def sync_course(body: SyncCourseRequest, db: Session = Depends(get_db)):
    result = platform_service.sync_course(
        db,
        platform_id=body.platformId,
        course_info=body.courseInfo,
    )

    return {
        "code": 200,
        "msg": "课程同步成功",
        "data": {
            **result,
            "syncTime": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "requestId": generate_request_id(),
    }


@router.post(
    "/syncUser",
    response_model=ApiResponse[SyncUserData],
    responses=_ERROR_RESPONSES,
    summary="用户信息同步",
    description="同步外部平台用户信息（教师/学生），支持权限校验与身份识别。",
)
def sync_user(body: SyncUserRequest, db: Session = Depends(get_db)):
    result = platform_service.sync_user(
        db,
        platform_id=body.platformId,
        user_info=body.userInfo,
    )

    return {
        "code": 200,
        "msg": "用户同步成功",
        "data": result,
        "requestId": generate_request_id(),
    }
