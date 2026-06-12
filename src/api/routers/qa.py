"""QA API routes."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.config import settings
from src.api.deps import generate_request_id
from src.api.models.database import get_db
from src.api.response_models import (
    ApiResponse,
    ErrorResponse,
    GamePayloadData,
    QAInteractData,
    VoiceToTextData,
)
from src.api.services import qa_service
from src.api.upload_utils import save_upload_file

router = APIRouter(prefix="/qa", tags=["qa"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Bad request"},
    404: {"model": ErrorResponse, "description": "Not found"},
}


class QAInteractRequest(BaseModel):
    schoolId: str
    userId: str
    courseId: str
    lessonId: str
    sessionId: str
    questionType: str = "text"
    questionContent: str
    currentSectionId: Optional[str] = None
    currentPage: Optional[int] = None
    currentScriptBlockId: Optional[str] = None
    historyQa: Optional[list[dict]] = None
    enc: str = ""
    time: str = ""


class VoiceToTextRequest(BaseModel):
    voiceUrl: str
    voiceDuration: Optional[int] = None
    language: str = "zh-CN"
    enc: str = ""
    time: str = ""


class GamePayloadRequest(BaseModel):
    schoolId: str = Field("", description="学校 ID")
    userId: str = Field("", description="用户 ID")
    courseId: str = Field("", description="课程 ID")
    lessonId: str
    sessionId: str
    question: str = ""
    currentSectionId: Optional[str] = None
    currentPage: Optional[int] = None
    enc: str = ""
    time: str = ""


def _success_response(data, msg: str) -> dict:
    return {
        "code": 200,
        "msg": msg,
        "data": data,
        "requestId": generate_request_id(),
    }


@router.post(
    "/interact",
    response_model=ApiResponse[QAInteractData],
    responses=_ERROR_RESPONSES,
)
def qa_interact(body: QAInteractRequest, db: Session = Depends(get_db)):
    session = qa_service.get_or_create_session(
        db,
        session_id=body.sessionId,
        user_id=body.userId,
        school_id=body.schoolId,
        course_id=body.courseId,
        lesson_id=body.lessonId,
    )

    result = qa_service.run_qa_interact(
        db,
        session=session,
        user_id=body.userId,
        question_type=body.questionType,
        question_content=body.questionContent,
        current_section_id=body.currentSectionId,
        current_page=body.currentPage,
        current_script_block_id=body.currentScriptBlockId,
        history_qa=body.historyQa,
    )

    return _success_response(result, "QA interaction completed")


@router.post(
    "/gamePayload",
    response_model=ApiResponse[GamePayloadData],
    responses=_ERROR_RESPONSES,
)
def qa_game_payload(body: GamePayloadRequest, db: Session = Depends(get_db)):
    session = qa_service.get_or_create_session(
        db,
        session_id=body.sessionId,
        user_id=body.userId,
        school_id=body.schoolId,
        course_id=body.courseId,
        lesson_id=body.lessonId,
    )

    result = qa_service.generate_game_payload(
        db,
        lesson_id=session.lesson_id,
        session_id=session.session_id,
        question=body.question,
        current_section_id=body.currentSectionId,
        current_page=body.currentPage,
    )

    payload = result or {
        "gameType": "multiple_choice",
        "prompt": "",
        "choices": [],
        "correctIndex": 0,
        "correctChoice": "",
        "explanation": "",
    }
    return _success_response(payload, "Game payload generated")


@router.post(
    "/voiceToText",
    response_model=ApiResponse[VoiceToTextData],
    responses=_ERROR_RESPONSES,
)
def voice_to_text(body: VoiceToTextRequest):
    result = qa_service.voice_to_text(
        voice_url=body.voiceUrl,
        language=body.language,
    )

    return _success_response(
        {
            "text": result["text"],
            "confidence": result["confidence"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "Voice recognized",
    )


@router.post(
    "/voiceToTextUpload",
    response_model=ApiResponse[VoiceToTextData],
    responses=_ERROR_RESPONSES,
)
async def voice_to_text_upload(
    language: str = Form("zh-CN"),
    file: UploadFile = File(...),
):
    saved_path, _, _ = await save_upload_file(file, settings.UPLOAD_DIR)
    result = qa_service.voice_to_text(
        voice_url=saved_path,
        language=language,
    )

    return _success_response(
        {
            "text": result["text"],
            "confidence": result["confidence"],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "Voice recognized",
    )
