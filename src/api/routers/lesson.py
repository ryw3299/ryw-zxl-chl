"""Lesson API routes."""

import json
import logging
import threading
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.api.config import settings
from src.api.deps import generate_id, generate_request_id
from src.api.models.database import SessionLocal, get_db
from src.api.models.tables import Lesson
from src.api.response_models import (
    ApiResponse,
    AudioData,
    ErrorResponse,
    ParseData,
    RenderData,
    ScriptData,
    WorkflowData,
)
from src.api.services import lesson_service
from src.api.upload_utils import normalize_bool, save_upload_file

router = APIRouter(prefix="/lesson", tags=["lesson"])

_ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Bad request"},
    404: {"model": ErrorResponse, "description": "Not found"},
}

logger = logging.getLogger(__name__)


class ParseRequest(BaseModel):
    schoolId: str
    userId: str
    courseId: str
    fileType: str
    fileUrl: str
    isExtractKeyPoint: bool = True
    enc: str = ""
    time: str = ""


class ScriptRequest(BaseModel):
    parseId: str
    teachingStyle: str = "standard"
    speechSpeed: str = "normal"
    customOpening: Optional[str] = None
    enc: str = ""
    time: str = ""


class AudioRequest(BaseModel):
    scriptId: str
    voiceType: str = "female_standard"
    audioFormat: str = "mp3"
    sectionIds: Optional[list[str]] = None
    enc: str = ""
    time: str = ""


class NarrationAudioRequest(BaseModel):
    lessonId: str
    levels: list[str] = Field(default_factory=lambda: ["A", "B", "C", "D"])
    voiceType: str = "female_standard"
    audioFormat: str = "mp3"
    sectionIds: Optional[list[str]] = None
    enc: str = ""
    time: str = ""


class NarrationAudioStatusRequest(BaseModel):
    lessonId: str
    enc: str = ""
    time: str = ""


class ParseStatusRequest(BaseModel):
    parseId: str
    enc: str = ""
    time: str = ""


class ScriptStatusRequest(BaseModel):
    scriptId: str
    enc: str = ""
    time: str = ""


class AudioStatusRequest(BaseModel):
    audioId: str
    enc: str = ""
    time: str = ""


class EditScriptRequest(BaseModel):
    scriptId: str
    scriptStructure: list[dict] = Field(default_factory=list)
    enc: str = ""
    time: str = ""


class GenerateRequest(BaseModel):
    schoolId: str
    userId: str
    courseId: str
    fileType: str
    fileUrl: str
    teachingStyle: str = "standard"
    customOpening: Optional[str] = None
    enc: str = ""
    time: str = ""


class GenerateStatusRequest(BaseModel):
    lessonId: str
    enc: str = ""
    time: str = ""


class RenderRequest(BaseModel):
    lessonId: str
    enc: str = ""
    time: str = ""


class CoursewareStatusRequest(BaseModel):
    lessonId: str
    enc: str = ""
    time: str = ""


class CoursewareSlidePlanRequest(BaseModel):
    lessonId: str
    slidePlan: dict
    enc: str = ""
    time: str = ""


class CoursewareRenderRequest(BaseModel):
    lessonId: str
    renderMode: str = "flash"
    enc: str = ""
    time: str = ""


class PublishRequest(BaseModel):
    lessonId: str
    lessonName: str
    courseDesc: Optional[str] = None
    tag: Optional[str] = None
    coverUrl: Optional[str] = None
    enc: str = ""
    time: str = ""


class DeleteLessonRequest(BaseModel):
    lessonId: str
    enc: str = ""
    time: str = ""


def _success_response(data, msg: str) -> dict:
    return {
        "code": 200,
        "msg": msg,
        "data": data,
        "requestId": generate_request_id(),
    }


def _error_response(status_code: int, msg: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": status_code,
            "msg": msg,
            "data": None,
            "requestId": generate_request_id(),
        },
    )


def _load_json(raw: Optional[str], fallback):
    if not raw:
        return fallback
    return json.loads(raw)


@router.post(
    "/parse",
    response_model=ApiResponse[ParseData],
    responses=_ERROR_RESPONSES,
)
def parse_courseware(
    body: ParseRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    task = lesson_service.create_parse_task(
        db,
        school_id=body.schoolId,
        user_id=body.userId,
        course_id=body.courseId,
        file_type=body.fileType,
        file_url=body.fileUrl,
        is_extract_key_point=body.isExtractKeyPoint,
    )

    background_tasks.add_task(_run_parse_in_background, task.parse_id)

    return _success_response(
        {
            "parseId": task.parse_id,
            "fileInfo": {
                "fileName": task.file_name,
                "fileSize": task.file_size or 0,
                "pageCount": 0,
            },
            "structurePreview": {},
            "taskStatus": "processing",
        },
        "Parse task submitted",
    )


@router.post(
    "/parseUpload",
    response_model=ApiResponse[ParseData],
    responses=_ERROR_RESPONSES,
)
async def parse_courseware_upload(
    background_tasks: BackgroundTasks,
    schoolId: str = Form(...),
    userId: str = Form(...),
    courseId: str = Form(...),
    fileType: str = Form(...),
    isExtractKeyPoint: str = Form("true"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    saved_path, original_name, file_size = await save_upload_file(
        file,
        settings.UPLOAD_DIR,
        preferred_suffix=fileType,
    )

    task = lesson_service.create_parse_task(
        db,
        school_id=schoolId,
        user_id=userId,
        course_id=courseId,
        file_type=fileType,
        file_url=saved_path,
        file_name=original_name,
        file_size=file_size,
        is_extract_key_point=normalize_bool(isExtractKeyPoint, default=True),
    )

    background_tasks.add_task(_run_parse_in_background, task.parse_id)

    return _success_response(
        {
            "parseId": task.parse_id,
            "fileInfo": {
                "fileName": task.file_name,
                "fileSize": task.file_size or 0,
                "pageCount": 0,
            },
            "structurePreview": {},
            "taskStatus": "processing",
        },
        "Parse task submitted",
    )


@router.post(
    "/courseware/slidePlanUpload",
    responses=_ERROR_RESPONSES,
)
async def create_courseware_slide_plan_upload(
    background_tasks: BackgroundTasks,
    schoolId: str = Form(...),
    userId: str = Form(...),
    courseId: str = Form(...),
    fileType: str = Form(...),
    instruction: str = Form(""),
    audience: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    saved_path, original_name, file_size = await save_upload_file(
        file,
        settings.UPLOAD_DIR,
        preferred_suffix=fileType,
    )

    lesson = lesson_service.create_courseware_slide_plan_task(
        db,
        school_id=schoolId,
        user_id=userId,
        course_id=courseId,
        file_type=fileType,
        file_url=saved_path,
        file_name=original_name,
        file_size=file_size,
        instruction=instruction,
        audience=audience,
    )

    background_tasks.add_task(_run_courseware_slide_plan_in_background, lesson.lesson_id)

    return _success_response(
        {
            "lessonId": lesson.lesson_id,
            "lessonName": lesson.lesson_name,
            "taskStatus": lesson.courseware_status,
        },
        "Courseware slide plan generation started",
    )


@router.post(
    "/courseware/status",
    responses=_ERROR_RESPONSES,
)
def get_courseware_status(body: CoursewareStatusRequest, db: Session = Depends(get_db)):
    result = lesson_service.get_courseware_status(db, body.lessonId)
    if result is None:
        return _error_response(404, "Lesson not found")
    return _success_response(result, "Courseware status fetched")


@router.post(
    "/courseware/slidePlan",
    responses=_ERROR_RESPONSES,
)
def update_courseware_slide_plan(body: CoursewareSlidePlanRequest, db: Session = Depends(get_db)):
    try:
        lesson = lesson_service.update_courseware_slide_plan(
            db,
            lesson_id=body.lessonId,
            slide_plan=body.slidePlan,
        )
    except ValueError as exc:
        return _error_response(400, str(exc))
    if lesson is None:
        return _error_response(404, "Lesson not found")
    return _success_response(
        {
            "lessonId": lesson.lesson_id,
            "taskStatus": lesson.courseware_status,
            "slidePlan": _load_json(lesson.slide_plan_json, {}),
        },
        "Slide plan updated",
    )


@router.post(
    "/courseware/render",
    responses=_ERROR_RESPONSES,
)
def render_courseware(
    body: CoursewareRenderRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    try:
        lesson = lesson_service.start_courseware_render(db, body.lessonId, body.renderMode)
    except ValueError as exc:
        return _error_response(400, str(exc))
    if lesson is None:
        return _error_response(404, "Lesson not found")

    background_tasks.add_task(_run_courseware_render_in_background, body.lessonId, lesson.courseware_render_mode or "flash")

    return _success_response(
        {
            "lessonId": lesson.lesson_id,
            "taskStatus": lesson.courseware_status,
            "renderMode": lesson.courseware_render_mode,
        },
        "Courseware render started",
    )


@router.post(
    "/parseStatus",
    response_model=ApiResponse[ParseData],
    responses=_ERROR_RESPONSES,
)
def get_parse_status(body: ParseStatusRequest, db: Session = Depends(get_db)):
    task = lesson_service.get_parse_task(db, body.parseId)
    if task is None:
        return _error_response(404, "Parse task not found")

    return _success_response(
        {
            "parseId": task.parse_id,
            "fileInfo": {
                "fileName": task.file_name,
                "fileSize": task.file_size or 0,
                "pageCount": task.page_count or 0,
            },
            "structurePreview": _load_json(task.structure_preview, {}),
            "taskStatus": task.task_status,
            "errorMessage": task.error_message,
        },
        "Parse status fetched",
    )


@router.post(
    "/generateScript",
    response_model=ApiResponse[ScriptData],
    responses=_ERROR_RESPONSES,
)
def generate_script(
    body: ScriptRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    parse_task = lesson_service.get_parse_task(db, body.parseId)
    if parse_task is None:
        return _error_response(404, "Parse task not found")
    if parse_task.task_status != "completed":
        return _error_response(
            400,
            f"Parse task is {parse_task.task_status}; wait until it completes",
        )

    script = lesson_service.create_script(
        db,
        parse_id=body.parseId,
        teaching_style=body.teachingStyle,
        speech_speed=body.speechSpeed,
        custom_opening=body.customOpening,
    )

    background_tasks.add_task(_run_generate_in_background, script.script_id)

    return _success_response(
        {
            "scriptId": script.script_id,
            "scriptStructure": [],
            "taskStatus": "processing",
            "editUrl": f"/script/edit?scriptId={script.script_id}",
            "audioGenerateUrl": "/api/v1/lesson/generateAudio",
        },
        "Script generation started",
    )


@router.post(
    "/scriptStatus",
    response_model=ApiResponse[ScriptData],
    responses=_ERROR_RESPONSES,
)
def get_script_status(body: ScriptStatusRequest, db: Session = Depends(get_db)):
    script = lesson_service.get_script(db, body.scriptId)
    if script is None:
        return _error_response(404, "Script task not found")
    audio = lesson_service.get_latest_completed_audio_for_script(db, script.script_id)

    return _success_response(
        {
            "scriptId": script.script_id,
            "parseId": script.parse_id,
            "lessonId": script.lesson_id,
            "audioId": audio.audio_id if audio else "",
            "audioUrl": audio.audio_url if audio else "",
            "teachingStyle": script.teaching_style,
            "taskStatus": script.task_status,
            "scriptStructure": _load_json(script.script_structure, []),
            "editUrl": f"/script/edit?scriptId={script.script_id}",
            "audioGenerateUrl": "/api/v1/lesson/generateAudio",
            "errorMessage": script.error_message,
        },
        "Script status fetched",
    )


@router.post(
    "/generateAudio",
    response_model=ApiResponse[AudioData],
    responses=_ERROR_RESPONSES,
)
def generate_audio(
    body: AudioRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    script = lesson_service.get_script(db, body.scriptId)
    if script is None:
        return _error_response(404, "Script not found")
    if script.task_status != "completed":
        return _error_response(
            400,
            f"Script is {script.task_status}; wait until it completes",
        )

    audio = lesson_service.create_audio_task(
        db,
        script_id=body.scriptId,
        voice_type=body.voiceType,
        audio_format=body.audioFormat,
        section_ids=body.sectionIds,
    )

    background_tasks.add_task(_run_audio_in_background, audio.audio_id)

    return _success_response(
        {
            "audioId": audio.audio_id,
            "taskStatus": "processing",
        },
        "Audio generation started",
    )


@router.post(
    "/audioStatus",
    response_model=ApiResponse[AudioData],
    responses=_ERROR_RESPONSES,
)
def get_audio_status(body: AudioStatusRequest, db: Session = Depends(get_db)):
    audio = lesson_service.get_audio_task(db, body.audioId)
    if audio is None:
        return _error_response(404, "Audio task not found")

    return _success_response(
        {
            "audioId": audio.audio_id,
            "taskStatus": audio.task_status,
            "audioUrl": audio.audio_url,
            "audioInfo": {
                "totalDuration": audio.total_duration or 0,
                "fileSize": audio.file_size or 0,
                "format": audio.audio_format,
                "bitRate": audio.bit_rate or 128000,
            },
            "sectionAudios": _load_json(audio.section_audios, []),
            "errorMessage": audio.error_message,
        },
        "Audio status fetched",
    )


@router.post(
    "/courseware/generateNarrationAudio",
    responses=_ERROR_RESPONSES,
)
def generate_narration_audio(
    body: NarrationAudioRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    levels = []
    for level in body.levels or ["A", "B", "C", "D"]:
        normalized = (level or "").upper()
        if normalized in {"A", "B", "C", "D"} and normalized not in levels:
            levels.append(normalized)
    if not levels:
        return _error_response(400, "levels must contain A/B/C/D")

    audio_tasks = {}
    audio_ids = []
    for level in levels:
        try:
            audio = lesson_service.create_narration_audio_task(
                db,
                lesson_id=body.lessonId,
                level=level,
                voice_type=body.voiceType,
                audio_format=body.audioFormat,
                section_ids=body.sectionIds,
            )
        except ValueError as exc:
            return _error_response(400, str(exc))
        if audio is None:
            return _error_response(404, f"Narration {level} not found")
        audio_ids.append(audio.audio_id)
        audio_tasks[level] = {
            "level": level,
            "audioId": audio.audio_id,
            "taskStatus": "processing",
        }

    _start_threaded_task(
        f"narration-audio-{body.lessonId}",
        _run_narration_audio_batch_in_background,
        audio_ids,
    )

    return _success_response(
        {
            "lessonId": body.lessonId,
            "audioTasks": audio_tasks,
        },
        "Narration audio generation started",
    )


@router.post(
    "/courseware/narrationAudioStatus",
    responses=_ERROR_RESPONSES,
)
def get_narration_audio_status(body: NarrationAudioStatusRequest, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.lesson_id == body.lessonId).first()
    if lesson is None:
        return _error_response(404, "Lesson not found")
    return _success_response(
        {
            "lessonId": body.lessonId,
            "audioTasks": lesson_service.get_narration_audio_tasks(db, body.lessonId),
        },
        "Narration audio status fetched",
    )


@router.post(
    "/editScript",
    response_model=ApiResponse[ScriptData],
    responses=_ERROR_RESPONSES,
)
def edit_script(body: EditScriptRequest, db: Session = Depends(get_db)):
    script = lesson_service.edit_script(
        db,
        script_id=body.scriptId,
        script_structure=body.scriptStructure,
    )
    if script is None:
        return _error_response(404, "Script not found")

    return _success_response(
        {
            "scriptId": script.script_id,
            "scriptStructure": _load_json(script.script_structure, []),
            "taskStatus": script.task_status,
            "editUrl": f"/script/edit?scriptId={script.script_id}",
            "audioGenerateUrl": "/api/v1/lesson/generateAudio",
        },
        "Script updated",
    )


@router.post(
    "/generate",
    response_model=ApiResponse[WorkflowData],
    responses=_ERROR_RESPONSES,
)
def generate_lesson(
    body: GenerateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    lesson_id = generate_id("lesson")
    lesson = Lesson(
        lesson_id=lesson_id,
        course_id=body.courseId,
        lesson_name="",
        status="generating",
    )
    db.add(lesson)
    db.commit()

    background_tasks.add_task(
        _run_workflow_in_background,
        lesson_id=lesson_id,
        school_id=body.schoolId,
        user_id=body.userId,
        course_id=body.courseId,
        file_type=body.fileType,
        file_url=body.fileUrl,
        teaching_style=body.teachingStyle,
        custom_opening=body.customOpening or "",
    )

    return _success_response(
        {
            "lessonId": lesson_id,
            "lessonName": "",
            "workflowStatus": "processing",
            "steps": [
                {"step": "Parse", "status": "processing"},
                {"step": "Script", "status": "pending"},
                {"step": "Render", "status": "pending"},
            ],
        },
        "Lesson generation started",
    )


@router.post(
    "/generateStatus",
    response_model=ApiResponse[WorkflowData],
    responses=_ERROR_RESPONSES,
)
def generate_status(
    body: GenerateStatusRequest,
    db: Session = Depends(get_db),
):
    result = lesson_service.get_workflow_status(db, body.lessonId)
    if result is None:
        return _error_response(404, "Lesson not found")

    return _success_response(result, "Workflow status fetched")


@router.post(
    "/renderPPT",
    response_model=ApiResponse[RenderData],
    responses=_ERROR_RESPONSES,
)
def render_ppt_endpoint(
    body: RenderRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    lesson = db.query(Lesson).filter(Lesson.lesson_id == body.lessonId).first()
    if lesson is None:
        return _error_response(404, "Lesson not found")
    if not lesson.ppt_outline:
        return _error_response(400, "PPT outline not found for lesson")

    background_tasks.add_task(_run_render_in_background, body.lessonId)

    return _success_response(
        {
            "lessonId": lesson.lesson_id,
            "taskStatus": "processing",
        },
        "PPT render started",
    )


@router.get(
    "/list",
    responses=_ERROR_RESPONSES,
)
def list_lessons(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    lessons = lesson_service.list_lessons(db, status=status)
    return _success_response({"lessons": lessons, "total": len(lessons)}, "Lessons fetched")


@router.post(
    "/publish",
    responses=_ERROR_RESPONSES,
)
def publish_lesson(
    body: PublishRequest,
    db: Session = Depends(get_db),
):
    lesson = lesson_service.publish_lesson(
        db,
        lesson_id=body.lessonId,
        lesson_name=body.lessonName,
        course_desc=body.courseDesc,
        tag=body.tag,
        cover_url=body.coverUrl,
    )
    if lesson is None:
        return _error_response(404, "Lesson not found")

    return _success_response(
        {
            "lessonId": lesson.lesson_id,
            "lessonName": lesson.lesson_name,
            "tag": (body.tag or "").strip(),
            "coverUrl": (body.coverUrl or "").strip(),
            "status": lesson.status,
        },
        "Lesson published",
    )


@router.post(
    "/delete",
    responses=_ERROR_RESPONSES,
)
def delete_lesson(
    body: DeleteLessonRequest,
    db: Session = Depends(get_db),
):
    lesson = lesson_service.archive_lesson(db, body.lessonId)
    if lesson is None:
        return _error_response(404, "Lesson not found")

    return _success_response(
        {
            "lessonId": lesson.lesson_id,
            "status": lesson.status,
        },
        "Lesson deleted",
    )


@router.get(
    "/download/{lessonId}",
    responses={
        **_ERROR_RESPONSES,
        200: {"content": {"application/vnd.openxmlformats-officedocument.presentationml.presentation": {}}},
    },
)
def download_ppt(lessonId: str, db: Session = Depends(get_db)):
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lessonId).first()
    if lesson is None or not lesson.rendered_ppt_path:
        return _error_response(404, "Rendered PPT not found")

    ppt_path = Path(lesson.rendered_ppt_path)
    if not ppt_path.exists():
        return _error_response(404, "Rendered PPT file is missing")

    download_name = f"{lesson.lesson_name or lesson.lesson_id}.pptx"
    return FileResponse(
        path=str(ppt_path),
        filename=download_name,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )


@router.get(
    "/narration/{lessonId}/{level}",
    responses=_ERROR_RESPONSES,
)
def get_narration(lessonId: str, level: str, db: Session = Depends(get_db)):
    try:
        result = lesson_service.get_courseware_narration(db, lessonId, level)
    except ValueError as exc:
        return _error_response(400, str(exc))
    if result is None:
        return _error_response(404, "Narration not found")
    return _success_response(result, "Narration fetched")


@router.get("/preview/{lessonId}")
def get_preview_meta(lessonId: str, db: Session = Depends(get_db)):
    result = lesson_service.get_preview_meta(db, lessonId)
    if result is None:
        return _error_response(404, "Lesson not found")

    return _success_response(result, "Preview status fetched")


@router.get(
    "/preview/{lessonId}/{slideNumber}",
    responses={
        **_ERROR_RESPONSES,
        200: {"content": {"image/png": {}}},
    },
)
def get_preview_image(
    lessonId: str,
    slideNumber: int,
    db: Session = Depends(get_db),
):
    image_path, error_message = lesson_service.get_preview_image_path(
        db,
        lessonId,
        slideNumber,
    )
    if image_path is None:
        return _error_response(404, error_message or "Preview image not found")

    return FileResponse(path=str(image_path), media_type="image/png")


_AUDIO_MEDIA_TYPES = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "ogg": "audio/ogg",
    "m4a": "audio/mp4",
}


@router.get(
    "/audio/{audio_id}/{section_id}",
    responses={
        **_ERROR_RESPONSES,
        200: {"content": {"audio/mpeg": {}, "audio/wav": {}}},
    },
)
def get_audio_file(audio_id: str, section_id: str, db: Session = Depends(get_db)):
    audio = lesson_service.get_audio_task(db, audio_id)
    if audio is None:
        return _error_response(404, "Audio task not found")
    if audio.task_status != "completed":
        return _error_response(400, f"Audio is {audio.task_status}; not ready for download")

    audio_format = (audio.audio_format or "mp3").lower()
    audio_path = Path(settings.AUDIO_DIR) / audio_id / f"{section_id}.{audio_format}"
    if not audio_path.exists():
        return _error_response(404, "Audio file not found")

    media_type = _AUDIO_MEDIA_TYPES.get(audio_format, "application/octet-stream")
    return FileResponse(path=str(audio_path), media_type=media_type)


def _run_parse_in_background(parse_id: str) -> None:
    db = SessionLocal()
    try:
        task = lesson_service.get_parse_task(db, parse_id)
        if task and task.task_status == "processing":
            lesson_service.run_parse_task(db, task)
    finally:
        db.close()


def _run_courseware_slide_plan_in_background(lesson_id: str) -> None:
    db = SessionLocal()
    try:
        lesson_service.run_courseware_slide_plan_task(db, lesson_id)
    except Exception:
        logger.exception("Courseware slide plan background task failed for lesson %s", lesson_id)
    finally:
        db.close()


def _run_courseware_render_in_background(lesson_id: str, render_mode: str) -> None:
    db = SessionLocal()
    try:
        lesson_service.run_courseware_render_task(db, lesson_id, render_mode)
    except Exception:
        logger.exception("Courseware render background task failed for lesson %s", lesson_id)
    finally:
        db.close()


def _run_generate_in_background(script_id: str) -> None:
    db = SessionLocal()
    try:
        script = lesson_service.get_script(db, script_id)
        if script and script.task_status == "processing":
            lesson_service.run_generate_script(db, script)
    finally:
        db.close()


def _run_audio_in_background(audio_id: str) -> None:
    db = SessionLocal()
    try:
        audio = lesson_service.get_audio_task(db, audio_id)
        if audio and audio.task_status == "processing":
            lesson_service.run_audio_task(db, audio)
    finally:
        db.close()


def _run_narration_audio_in_background(audio_id: str) -> None:
    db = SessionLocal()
    try:
        audio = lesson_service.get_audio_task(db, audio_id)
        if audio and audio.task_status == "processing":
            lesson_service.run_narration_audio_task(db, audio)
    finally:
        db.close()


def _run_narration_audio_batch_in_background(audio_ids: list[str]) -> None:
    for audio_id in audio_ids:
        try:
            _run_narration_audio_in_background(audio_id)
        except Exception:
            logger.exception("Narration audio background task failed for audio %s", audio_id)


def _start_threaded_task(name: str, target, *args) -> None:
    thread = threading.Thread(target=target, args=args, name=name, daemon=True)
    thread.start()


def _run_workflow_in_background(
    *,
    lesson_id: str,
    school_id: str,
    user_id: str,
    course_id: str,
    file_type: str,
    file_url: str,
    teaching_style: str,
    custom_opening: str,
) -> None:
    db = SessionLocal()
    try:
        lesson_service.run_full_workflow(
            db,
            lesson_id=lesson_id,
            school_id=school_id,
            user_id=user_id,
            course_id=course_id,
            file_type=file_type,
            file_url=file_url,
            teaching_style=teaching_style,
            custom_opening=custom_opening,
        )
    finally:
        db.close()


def _run_render_in_background(lesson_id: str) -> None:
    db = SessionLocal()
    try:
        lesson_service.render_ppt_for_lesson(db, lesson_id)
    except Exception:
        logger.exception("PPT render failed for lesson %s", lesson_id)
    finally:
        db.close()
