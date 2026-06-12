"""智课服务层 (Lesson Service Layer).

This module is the *only* place that orchestrates the four-stage teacher
workflow on top of the database.  Higher layers (FastAPI routers) call
into the public functions defined here without ever touching pipelines
or pptx renderers directly.

Public surface
--------------
* :func:`create_parse_task` / :func:`run_parse_task` - file → structured content
* :func:`create_script` / :func:`run_generate_script` - structured → narration
* :func:`create_audio_task` / :func:`run_audio_task` - narration → mp3
* :func:`run_full_workflow` - one-shot teacher pipeline
* :func:`render_ppt_for_lesson` / :func:`get_preview_meta` - PPT artifacts
* :func:`publish_lesson` / :func:`archive_lesson` / :func:`list_lessons` - lifecycle

All write paths go through SQLAlchemy ``Session`` and commit explicitly
so request-level transactions stay bounded.  Long-running stages (parse
/ script / audio) update the corresponding ``task_status`` column so the
client can poll ``/parseStatus`` / ``/generateScript`` etc.
"""

import asyncio
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse
from urllib.request import urlretrieve

from sqlalchemy.orm import Session

from src.api.config import settings
from src.api.deps import generate_id
from src.api.models.tables import AudioTask, Lesson, ParseTask, Script

logger = logging.getLogger(__name__)


def _load_json(raw: Optional[str], default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


def create_parse_task(
    db: Session,
    *,
    school_id: str,
    user_id: str,
    course_id: str,
    file_type: str,
    file_url: str,
    file_name: Optional[str] = None,
    file_size: Optional[int] = None,
    is_extract_key_point: bool = True,
) -> ParseTask:
    """Create a new ``ParseTask`` row in ``processing`` state.

    Returns the persisted row immediately; the status field is updated
    asynchronously by :func:`run_parse_task` to ``completed`` or
    ``failed``.
    """
    parse_id = generate_id("parse")
    resolved_file_name = file_name or Path(urlparse(file_url).path).name or f"upload.{file_type}"
    resolved_file_size = file_size if file_size is not None else _get_file_size(file_url)

    task = ParseTask(
        parse_id=parse_id,
        school_id=school_id,
        user_id=user_id,
        course_id=course_id,
        file_type=file_type,
        file_url=file_url,
        file_name=resolved_file_name,
        file_size=resolved_file_size,
        is_extract_key_point=is_extract_key_point,
        task_status="processing",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def run_parse_task(db: Session, task: ParseTask) -> dict:
    """Execute the actual parsing pipeline and update the task record."""
    from src.agents.file_parser import build_file_parser_stages

    file_path = task.file_url
    if file_path.startswith("http"):
        file_path = _download_to_local(file_path, task.file_type)
        if task.file_size is None or task.file_size == 0:
            task.file_size = _get_file_size(file_path)

    parser_request = {
        "course_id": task.course_id,
        "lesson_id": task.parse_id,
        "assets": [
            {
                "file_path": file_path,
                "file_type": task.file_type,
                "file_name": task.file_name,
            }
        ],
        "parse_instruction": None,
    }

    try:
        stages = build_file_parser_stages(
            parser_request,
            env_path=settings.LLM_ENV_PATH,
        )
        output = stages["output"]
        output_dict = output.model_dump(mode="python")

        structured_content = stages["structured_content"]
        pages = list(structured_content.pages)
        sections = list(structured_content.sections)

        structure_preview = _build_structure_preview(sections, pages)
        page_count = len(pages)

        task.task_status = "completed"
        task.page_count = page_count
        task.structure_preview = json.dumps(structure_preview, ensure_ascii=False)
        task.parser_output = json.dumps(output_dict, ensure_ascii=False)

        _ensure_lesson(
            db,
            lesson_id=task.parse_id,
            course_id=task.course_id,
            lesson_name=task.file_name,
            parse_id=task.parse_id,
            structured_content=structured_content.model_dump(mode="python"),
        )

    except Exception as exc:
        task.task_status = "failed"
        task.error_message = str(exc)
        structure_preview = {}

    db.commit()
    db.refresh(task)
    return _format_parse_result(task, structure_preview)


def get_parse_task(db: Session, parse_id: str) -> Optional[ParseTask]:
    """Look up a parse task by its ``parse_id`` (returns ``None`` if missing)."""
    return db.query(ParseTask).filter(ParseTask.parse_id == parse_id).first()


def create_script(
    db: Session,
    *,
    parse_id: str,
    teaching_style: str = "standard",
    speech_speed: str = "normal",
    custom_opening: Optional[str] = None,
) -> Script:
    """Create a ``Script`` row scoped to a lesson, ready for generation.

    The row is in ``pending`` state until
    :func:`run_generate_script` populates the narration text.
    """
    script_id = generate_id("script")
    script = Script(
        script_id=script_id,
        parse_id=parse_id,
        teaching_style=teaching_style,
        speech_speed=speech_speed,
        custom_opening=custom_opening,
        task_status="processing",
    )
    db.add(script)
    db.commit()
    db.refresh(script)
    return script


def run_generate_script(db: Session, script: Script) -> dict:
    """Execute the generate pipeline and update the script record."""
    from src.agents.generate import build_generate_stages

    parse_task = get_parse_task(db, script.parse_id)
    if parse_task is None or parse_task.task_status != "completed":
        script.task_status = "failed"
        script.error_message = "关联的解析任务不存在或尚未完成"
        db.commit()
        return {"error": script.error_message}

    parser_output = json.loads(parse_task.parser_output)
    structured_content = parser_output.get("structured_content", {})

    lesson_name = parse_task.file_name
    generate_instruction = ""
    if script.teaching_style == "detailed":
        generate_instruction = "请生成更详细的讲解内容，并对每个知识点进行充分展开。"
    elif script.teaching_style == "concise":
        generate_instruction = "请生成更简洁的讲解内容，突出核心知识点。"

    teacher_notes = script.custom_opening or ""

    generate_request = {
        "course_id": parse_task.course_id,
        "lesson_id": parse_task.parse_id,
        "lesson_name": lesson_name,
        "structured_content": structured_content,
        "teacher_notes": teacher_notes,
        "generate_instruction": generate_instruction,
    }

    try:
        stages = build_generate_stages(
            generate_request,
            env_path=settings.LLM_ENV_PATH,
        )
        output = stages["output"]
        output_dict = output.model_dump(mode="python")

        script_structure = _build_script_structure(stages)
        lesson_script_obj = stages.get("lesson_script")
        if lesson_script_obj:
            output_dict["lesson_script"] = lesson_script_obj.model_dump(mode="python")
        script.task_status = "completed"
        script.script_structure = json.dumps(script_structure, ensure_ascii=False)
        script.generate_output = json.dumps(output_dict, ensure_ascii=False)
        script.lesson_id = parse_task.parse_id

        lesson = db.query(Lesson).filter(Lesson.lesson_id == parse_task.parse_id).first()
        if lesson:
            lesson.script_id = script.script_id
            ppt_outline = stages.get("ppt_outline")
            if ppt_outline:
                lesson.ppt_outline = json.dumps(ppt_outline.model_dump(mode="python"), ensure_ascii=False)

    except Exception as exc:
        script.task_status = "failed"
        script.error_message = str(exc)
        script_structure = []

    db.commit()
    db.refresh(script)
    return _format_script_result(script, script_structure)


def get_script(db: Session, script_id: str) -> Optional[Script]:
    """Look up a script by its ``script_id`` (returns ``None`` if missing)."""
    return db.query(Script).filter(Script.script_id == script_id).first()


def get_audio_task(db: Session, audio_id: str) -> Optional[AudioTask]:
    """Look up an audio task by its ``audio_id`` (returns ``None`` if missing)."""
    return db.query(AudioTask).filter(AudioTask.audio_id == audio_id).first()


def get_latest_completed_audio_for_script(db: Session, script_id: str) -> Optional[AudioTask]:
    """Return the most recently completed ``AudioTask`` for a script.

    Useful for the ``/audio/{audio_id}/{section}`` download endpoint
    where the client only knows ``script_id``.
    """
    if not script_id:
        return None
    return (
        db.query(AudioTask)
        .filter(AudioTask.script_id == script_id, AudioTask.task_status == "completed")
        .order_by(AudioTask.created_at.desc())
        .first()
    )


def _narration_script_id(lesson_id: str, level: str) -> str:
    return f"narration:{lesson_id}:{level.upper()}"


def _safe_audio_id_part(value: str, max_len: int = 24) -> str:
    cleaned = "".join(
        ch.lower() if ch.isascii() and (ch.isalnum() or ch in {"_", "-"}) else "_"
        for ch in str(value or "")
    ).strip("_")
    return (cleaned or "lesson")[:max_len]


def _narration_audio_id(lesson_id: str, level: str) -> str:
    lesson_part = _safe_audio_id_part(lesson_id)
    return f"audio_{lesson_part}_{level.upper()}_{uuid.uuid4().hex[:10]}"


def get_narration_audio_tasks(db: Session, lesson_id: str) -> dict[str, dict]:
    """Return latest audio task metadata for each narration detail level."""
    result: dict[str, dict] = {}
    for level in ("A", "B", "C", "D"):
        task = (
            db.query(AudioTask)
            .filter(AudioTask.script_id == _narration_script_id(lesson_id, level))
            .order_by(AudioTask.created_at.desc())
            .first()
        )
        if not task:
            continue
        result[level] = {
            "level": level,
            "audioId": task.audio_id,
            "taskStatus": task.task_status,
            "audioUrl": task.audio_url,
            "sectionAudios": _load_json(task.section_audios, []),
            "errorMessage": task.error_message,
        }
    return result


def create_audio_task(
    db: Session,
    *,
    script_id: str,
    voice_type: str = "female_standard",
    audio_format: str = "mp3",
    section_ids: Optional[list[str]] = None,
) -> AudioTask:
    """Create an ``AudioTask`` row in ``pending`` state.

    The row is queued for execution by :func:`run_audio_task`, which
    invokes the configured TTS backend (``edge-tts`` by default).
    """
    audio_id = generate_id("audio")
    audio = AudioTask(
        audio_id=audio_id,
        script_id=script_id,
        voice_type=voice_type,
        audio_format=audio_format,
        section_ids=json.dumps(section_ids or []),
        task_status="processing",
    )
    db.add(audio)
    db.commit()
    db.refresh(audio)
    return audio


def create_narration_audio_task(
    db: Session,
    *,
    lesson_id: str,
    level: str,
    voice_type: str = "female_standard",
    audio_format: str = "mp3",
    section_ids: Optional[list[str]] = None,
) -> Optional[AudioTask]:
    """Create an audio task backed by narration_A/B/C/D.json instead of scripts."""
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None or not lesson.narration_paths:
        return None
    normalized_level = (level or "").upper()
    if normalized_level not in {"A", "B", "C", "D"}:
        raise ValueError("level must be one of A/B/C/D")
    try:
        narration_paths = json.loads(lesson.narration_paths)
    except json.JSONDecodeError:
        return None
    narration_path = narration_paths.get(normalized_level)
    if not narration_path or not Path(narration_path).exists():
        return None

    audio_id = _narration_audio_id(lesson_id, normalized_level)
    audio = AudioTask(
        audio_id=audio_id,
        script_id=_narration_script_id(lesson_id, normalized_level),
        voice_type=voice_type,
        audio_format=audio_format,
        section_ids=json.dumps(section_ids or []),
        task_status="processing",
    )
    db.add(audio)
    db.commit()
    db.refresh(audio)
    return audio


def _narration_sections_from_payload(payload: dict, level: str) -> list[dict]:
    slides = payload.get("slides") if isinstance(payload, dict) else []
    sections: list[dict] = []
    if not isinstance(slides, list):
        return sections
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            continue
        slide_id = str(slide.get("slide_id") or index)
        text = str(slide.get("script") or slide.get("content") or "").strip()
        if not text:
            continue
        topic = str(slide.get("topic") or slide.get("title") or f"页面 {index}").strip()
        sections.append(
            {
                "sectionId": f"{level.upper()}-{slide_id}",
                "sectionName": topic,
                "content": text,
            }
        )
    return sections


def run_narration_audio_task(db: Session, audio: AudioTask) -> dict:
    """Synthesize audio from generated narration_A/B/C/D.json files."""
    from src.services.tts import synthesize_sections

    prefix = "narration:"
    if not audio.script_id.startswith(prefix):
        audio.task_status = "failed"
        audio.error_message = "音频任务不是讲稿音频任务"
        db.commit()
        return {"error": audio.error_message}

    _, lesson_id, level = audio.script_id.split(":", 2)
    narration = get_courseware_narration(db, lesson_id, level)
    if not narration:
        audio.task_status = "failed"
        audio.error_message = "四档讲稿不存在或尚未生成"
        db.commit()
        return {"error": audio.error_message}

    sections = _narration_sections_from_payload(narration.get("narration") or {}, level)
    if not sections:
        audio.task_status = "failed"
        audio.error_message = "讲稿内容为空，无法合成音频"
        db.commit()
        return {"error": audio.error_message}

    section_filter = None
    if audio.section_ids:
        try:
            ids = json.loads(audio.section_ids)
            section_filter = {str(i) for i in ids if i} or None
        except json.JSONDecodeError:
            section_filter = None

    audio_format = (audio.audio_format or "mp3").lower()
    output_dir = Path(settings.AUDIO_DIR) / audio.audio_id

    try:
        results = synthesize_sections(
            sections=sections,
            voice_type=audio.voice_type or "female_standard",
            output_dir=output_dir,
            audio_format=audio_format,
            section_filter=section_filter,
        )
    except Exception as exc:
        logger.exception("Narration audio task %s failed during synthesis", audio.audio_id)
        audio.task_status = "failed"
        audio.error_message = str(exc)[:500]
        db.commit()
        return {"error": audio.error_message}

    if not results:
        audio.task_status = "failed"
        audio.error_message = "没有可合成的讲稿片段"
        db.commit()
        return {"error": audio.error_message}

    total_duration = int(round(sum(r.duration_seconds for r in results)))
    total_size = sum(r.file_size for r in results)
    section_page_numbers = {
        str(section.get("sectionId")): index
        for index, section in enumerate(sections, start=1)
    }
    section_audios = [
        {
            "sectionId": r.section_id,
            "slideId": str(r.section_id).split("-", 1)[-1],
            "slideNumber": section_page_numbers.get(str(r.section_id)),
            "pageNumber": section_page_numbers.get(str(r.section_id)),
            "level": level.upper(),
            "audioUrl": f"{settings.API_V1_PREFIX}/lesson/audio/{audio.audio_id}/{r.section_id}",
            "duration": int(round(r.duration_seconds)),
            "fileSize": r.file_size,
        }
        for r in results
    ]

    first_section_id = results[0].section_id
    audio.task_status = "completed"
    audio.total_duration = total_duration
    audio.file_size = total_size
    audio.bit_rate = 48000
    audio.audio_url = f"{settings.API_V1_PREFIX}/lesson/audio/{audio.audio_id}/{first_section_id}"
    audio.section_audios = json.dumps(section_audios, ensure_ascii=False)
    audio.error_message = None
    db.commit()
    db.refresh(audio)
    return _format_audio_result(audio, section_audios)


def run_audio_task(db: Session, audio: AudioTask) -> dict:
    """调用 edge-tts 将脚本章节合成为音频文件，并把元数据写回 AudioTask。"""
    from src.services.tts import synthesize_sections

    script = get_script(db, audio.script_id)
    if script is None or script.task_status != "completed":
        audio.task_status = "failed"
        audio.error_message = "关联的脚本不存在或尚未完成"
        db.commit()
        return {"error": audio.error_message}

    script_structure = json.loads(script.script_structure) if script.script_structure else []
    if not script_structure:
        audio.task_status = "failed"
        audio.error_message = "脚本内容为空，无法合成音频"
        db.commit()
        return {"error": audio.error_message}

    section_filter = None
    if audio.section_ids:
        try:
            ids = json.loads(audio.section_ids)
            section_filter = {str(i) for i in ids if i} or None
        except json.JSONDecodeError:
            section_filter = None

    audio_format = (audio.audio_format or "mp3").lower()
    output_dir = Path(settings.AUDIO_DIR) / audio.audio_id

    try:
        results = synthesize_sections(
            sections=script_structure,
            voice_type=audio.voice_type or "female_standard",
            output_dir=output_dir,
            audio_format=audio_format,
            section_filter=section_filter,
        )
    except Exception as exc:
        logger.exception("Audio task %s failed during synthesis", audio.audio_id)
        audio.task_status = "failed"
        audio.error_message = str(exc)[:500]
        db.commit()
        return {"error": audio.error_message}

    if not results:
        audio.task_status = "failed"
        audio.error_message = "没有可合成的章节（检查 sectionIds 或脚本内容）"
        db.commit()
        return {"error": audio.error_message}

    total_duration = int(round(sum(r.duration_seconds for r in results)))
    total_size = sum(r.file_size for r in results)

    section_audios = [
        {
            "sectionId": r.section_id,
            "audioUrl": f"{settings.API_V1_PREFIX}/lesson/audio/{audio.audio_id}/{r.section_id}",
            "duration": int(round(r.duration_seconds)),
            "fileSize": r.file_size,
        }
        for r in results
    ]

    first_section_id = results[0].section_id
    audio.task_status = "completed"
    audio.total_duration = total_duration
    audio.file_size = total_size
    audio.bit_rate = 48000
    audio.audio_url = f"{settings.API_V1_PREFIX}/lesson/audio/{audio.audio_id}/{first_section_id}"
    audio.section_audios = json.dumps(section_audios, ensure_ascii=False)
    audio.error_message = None

    db.commit()
    db.refresh(audio)
    return _format_audio_result(audio, section_audios)


def edit_script(
    db: Session,
    *,
    script_id: str,
    script_structure: list[dict],
) -> Optional[Script]:
    """Allow teachers to update the generated script content."""
    script = get_script(db, script_id)
    if script is None:
        return None
    script.script_structure = json.dumps(script_structure, ensure_ascii=False)
    db.commit()
    db.refresh(script)
    return script


def run_full_workflow(
    db: Session,
    *,
    lesson_id: str,
    school_id: str,
    user_id: str,
    course_id: str,
    file_type: str,
    file_url: str,
    teaching_style: str = "standard",
    custom_opening: str = "",
) -> None:
    """执行完整教师流程：解析、生成脚本、渲染 PPT。"""
    from src.workflows.teacher_workflow import build_teacher_workflow_stages

    file_path = file_url
    file_name = Path(urlparse(file_url).path).name or f"upload.{file_type}"
    if file_path.startswith("http"):
        file_path = _download_to_local(file_path, file_type)
    file_size = _get_file_size(file_path)
    lesson_name = Path(file_name).stem

    generate_instruction = ""
    if teaching_style == "detailed":
        generate_instruction = "请生成更详细的讲解内容，并对每个知识点进行充分展开。"
    elif teaching_style == "concise":
        generate_instruction = "请生成更简洁的讲解内容，突出核心知识点。"

    teacher_input = {
        "course_id": course_id,
        "lesson_id": lesson_id,
        "lesson_name": lesson_name,
        "assets": [{"file_path": file_path, "file_type": file_type, "file_name": file_name}],
        "teacher_notes": custom_opening or "",
        "generate_instruction": generate_instruction,
    }

    render_dir = Path(settings.RENDER_DIR)
    render_dir.mkdir(parents=True, exist_ok=True)
    render_path = str(render_dir / f"{lesson_id}.pptx")

    try:
        stages = build_teacher_workflow_stages(
            teacher_input,
            env_path=settings.LLM_ENV_PATH,
            rendered_ppt_file=render_path,
        )

        parser_stages = stages["parser_stages"]
        generate_stages = stages["generate_stages"]
        structured_content = parser_stages["structured_content"]
        pages = list(structured_content.pages)
        sections = list(structured_content.sections)
        structure_preview = _build_structure_preview(sections, pages)
        script_structure = _build_script_structure(generate_stages)

        parser_output_dict = parser_stages["output"].model_dump(mode="python")
        generate_output_dict = generate_stages["output"].model_dump(mode="python")
        lesson_script_obj = generate_stages.get("lesson_script")
        if lesson_script_obj:
            generate_output_dict["lesson_script"] = lesson_script_obj.model_dump(mode="python")

        parse_task = ParseTask(
            parse_id=lesson_id,
            school_id=school_id,
            user_id=user_id,
            course_id=course_id,
            file_type=file_type,
            file_url=file_url,
            file_name=file_name,
            file_size=file_size,
            page_count=len(pages),
            is_extract_key_point=True,
            task_status="completed",
            structure_preview=json.dumps(structure_preview, ensure_ascii=False),
            parser_output=json.dumps(parser_output_dict, ensure_ascii=False),
        )
        db.add(parse_task)
        db.flush()

        script_id = generate_id("script")
        script = Script(
            script_id=script_id,
            parse_id=lesson_id,
            lesson_id=lesson_id,
            teaching_style=teaching_style,
            custom_opening=custom_opening or None,
            task_status="completed",
            script_structure=json.dumps(script_structure, ensure_ascii=False),
            generate_output=json.dumps(generate_output_dict, ensure_ascii=False),
        )
        db.add(script)
        db.flush()

        lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
        if lesson:
            lesson.lesson_name = lesson_name
            lesson.parse_id = lesson_id
            lesson.script_id = script_id
            lesson.structured_content = json.dumps(
                structured_content.model_dump(mode="python"), ensure_ascii=False
            )
            lesson.status = "draft"

            ppt_outline = generate_stages.get("ppt_outline")
            if ppt_outline:
                lesson.ppt_outline = json.dumps(ppt_outline.model_dump(mode="python"), ensure_ascii=False)

            rendered_ppt_path = stages.get("rendered_ppt_path")
            if rendered_ppt_path:
                lesson.rendered_ppt_path = str(rendered_ppt_path)

        db.commit()

    except Exception as exc:
        logger.exception("Full workflow failed for lesson %s", lesson_id)
        # Best-effort cleanup: rollback the transaction; ignore secondary
        # failures here (the original exception is what callers care about).
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            logger.debug("rollback after workflow failure also failed", exc_info=True)
        # Best-effort failure record so the lesson row reflects the error.
        try:
            lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
            if lesson:
                lesson.status = "failed"
            existing = db.query(ParseTask).filter(ParseTask.parse_id == lesson_id).first()
            if existing is None:
                db.add(
                    ParseTask(
                        parse_id=lesson_id,
                        school_id=school_id,
                        user_id=user_id,
                        course_id=course_id,
                        file_type=file_type,
                        file_url=file_url,
                        file_name=file_name,
                        file_size=file_size or 0,
                        task_status="failed",
                        error_message=str(exc),
                    )
                )
            db.commit()
        except Exception:  # noqa: BLE001
            logger.debug(
                "Could not persist failure record for lesson %s",
                lesson_id,
                exc_info=True,
            )


def create_courseware_slide_plan_task(
    db: Session,
    *,
    school_id: str,
    user_id: str,
    course_id: str,
    file_type: str,
    file_url: str,
    file_name: Optional[str] = None,
    file_size: Optional[int] = None,
    instruction: str = "",
    audience: str = "",
) -> Lesson:
    """Create a lesson row for the new slide_plan-first courseware workflow."""
    lesson_id = generate_id("lesson")
    resolved_file_name = file_name or Path(urlparse(file_url).path).name or f"upload.{file_type}"
    lesson_name = Path(resolved_file_name).stem or "未命名课件"
    metadata = {
        "_courseware": {
            "schoolId": school_id,
            "userId": user_id,
            "courseId": course_id,
            "fileType": file_type,
            "fileUrl": file_url,
            "fileName": resolved_file_name,
            "fileSize": file_size if file_size is not None else _get_file_size(file_url),
            "instruction": instruction,
            "audience": audience,
        }
    }
    lesson = Lesson(
        lesson_id=lesson_id,
        course_id=course_id,
        lesson_name=lesson_name,
        status="planning",
        structured_content=json.dumps(metadata, ensure_ascii=False),
        courseware_status="planning",
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    return lesson


def run_courseware_slide_plan_task(db: Session, lesson_id: str) -> None:
    """Generate slide_plan.json for the new PPT master courseware workflow."""
    from src.agents.courseware_flash_slideplan import run_courseware_flash_slideplan

    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None:
        return

    courseware_meta = _get_courseware_meta(lesson)
    file_url = courseware_meta.get("fileUrl") or ""
    file_type = courseware_meta.get("fileType") or "pptx"
    file_name = courseware_meta.get("fileName") or lesson.lesson_name
    material_path = file_url

    try:
        if material_path.startswith("http"):
            material_path = _download_to_local(material_path, file_type)

        instruction = _build_courseware_instruction(
            lesson_name=lesson.lesson_name or Path(file_name).stem,
            instruction=courseware_meta.get("instruction") or "",
        )
        result = asyncio.run(
            run_courseware_flash_slideplan(
                instruction=instruction,
                material_path=material_path,
                audience=courseware_meta.get("audience") or "",
                env_path=settings.LLM_ENV_PATH,
            )
        )

        slide_plan_path = Path(result["slide_plan_path"])
        slide_plan = _read_json_file(slide_plan_path)

        lesson.courseware_project_dir = result.get("project_dir")
        lesson.slide_plan_path = str(slide_plan_path)
        lesson.slide_plan_json = json.dumps(slide_plan, ensure_ascii=False, indent=2)
        lesson.ppt_outline = lesson.slide_plan_json
        lesson.courseware_status = "plan_ready"
        lesson.courseware_error = None
        lesson.status = "draft"
        if not lesson.lesson_name:
            lesson.lesson_name = slide_plan.get("deck_title") or Path(file_name).stem
        db.commit()
    except Exception as exc:
        logger.exception("Courseware slide plan generation failed for lesson %s", lesson_id)
        lesson.courseware_status = "failed"
        lesson.courseware_error = str(exc)[:1000]
        lesson.status = "failed"
        db.commit()


def get_courseware_status(db: Session, lesson_id: str) -> Optional[dict]:
    """Return courseware workflow status and editable slide plan."""
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None:
        return None

    slide_plan = None
    if lesson.slide_plan_json:
        try:
            slide_plan = json.loads(lesson.slide_plan_json)
        except json.JSONDecodeError:
            slide_plan = None

    narration_paths = {}
    if lesson.narration_paths:
        try:
            narration_paths = json.loads(lesson.narration_paths)
        except json.JSONDecodeError:
            narration_paths = {}

    return {
        "lessonId": lesson.lesson_id,
        "lessonName": lesson.lesson_name,
        "taskStatus": lesson.courseware_status or lesson.status,
        "renderMode": lesson.courseware_render_mode,
        "slidePlan": slide_plan,
        "slidePlanPath": lesson.slide_plan_path,
        "projectDir": lesson.courseware_project_dir,
        "renderedPptUrl": f"/api/v1/lesson/download/{lesson.lesson_id}" if lesson.rendered_ppt_path else None,
        "narrationPaths": narration_paths,
        "narrationAudioTasks": get_narration_audio_tasks(db, lesson.lesson_id),
        "errorMessage": lesson.courseware_error,
    }


def get_courseware_narration(db: Session, lesson_id: str, level: str) -> Optional[dict]:
    """Load one narration_A/B/C/D.json artifact for a lesson."""
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None or not lesson.narration_paths:
        return None

    try:
        paths_by_level = json.loads(lesson.narration_paths)
    except json.JSONDecodeError:
        return None

    normalized_level = (level or "").upper()
    if normalized_level not in {"A", "B", "C", "D"}:
        raise ValueError("level must be one of A/B/C/D")

    narration_path = paths_by_level.get(normalized_level)
    if not narration_path:
        return None
    path = Path(narration_path)
    if not path.exists():
        return None
    payload = _read_json_file(path)
    return {
        "lessonId": lesson.lesson_id,
        "level": normalized_level,
        "narration": payload,
    }


def update_courseware_slide_plan(
    db: Session,
    *,
    lesson_id: str,
    slide_plan: dict,
) -> Optional[Lesson]:
    """Persist teacher-edited slide_plan.json both in DB and on disk."""
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None:
        return None
    _validate_slide_plan_payload(slide_plan)

    slide_plan_text = json.dumps(slide_plan, ensure_ascii=False, indent=2)
    if lesson.slide_plan_path:
        slide_plan_path = Path(lesson.slide_plan_path).resolve()
        project_dir = Path(lesson.courseware_project_dir).resolve() if lesson.courseware_project_dir else slide_plan_path.parent
        if project_dir not in (slide_plan_path, *slide_plan_path.parents):
            raise ValueError("slide_plan_path is outside project directory")
        slide_plan_path.write_text(slide_plan_text, encoding="utf-8")

    lesson.slide_plan_json = slide_plan_text
    lesson.ppt_outline = slide_plan_text
    lesson.courseware_status = "plan_ready"
    lesson.courseware_error = None
    db.commit()
    db.refresh(lesson)
    return lesson


def start_courseware_render(db: Session, lesson_id: str, render_mode: str = "flash") -> Optional[Lesson]:
    """Mark a courseware lesson as rendering before a background render task."""
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None:
        return None
    if not lesson.slide_plan_json:
        raise ValueError("slide_plan is not ready")
    mode = render_mode if render_mode in {"flash", "pro"} else "flash"
    lesson.courseware_status = "rendering"
    lesson.courseware_render_mode = mode
    lesson.courseware_error = None
    lesson.status = "rendering"
    db.commit()
    db.refresh(lesson)
    return lesson


def run_courseware_render_task(db: Session, lesson_id: str, render_mode: str = "flash") -> None:
    """Render PPTX with flash/pro mode and generate narration_A/B/C/D files."""
    from src.agents.courseware_flash_narration import run_courseware_flash_narration
    from src.agents.courseware_flash_render import run_courseware_flash_render
    from src.agents.courseware_pro_render import run_courseware_pro_render

    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None:
        return

    try:
        if lesson.slide_plan_json and lesson.slide_plan_path:
            update_courseware_slide_plan(
                db,
                lesson_id=lesson_id,
                slide_plan=json.loads(lesson.slide_plan_json),
            )
            lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
            if lesson is None:
                return
            lesson.courseware_status = "rendering"
            lesson.status = "rendering"
            db.commit()

        project_dir = lesson.courseware_project_dir
        slide_plan_path = lesson.slide_plan_path
        if not project_dir and not slide_plan_path:
            raise ValueError("slide_plan project is not ready")

        if render_mode == "pro":
            render_result = asyncio.run(
                run_courseware_pro_render(
                    project_dir=project_dir,
                    slide_plan_path=slide_plan_path,
                    audience=_get_courseware_meta(lesson).get("audience") or "",
                    env_path=settings.LLM_ENV_PATH,
                    generate_narration=False,
                )
            )
        else:
            render_result = asyncio.run(
                run_courseware_flash_render(
                    project_dir=project_dir,
                    slide_plan_path=slide_plan_path,
                    env_path=settings.LLM_ENV_PATH,
                )
            )

        narration_result = asyncio.run(
            run_courseware_flash_narration(
                project_dir=project_dir,
                slide_plan_path=slide_plan_path,
                audience=_get_courseware_meta(lesson).get("audience") or "",
                env_path=settings.LLM_ENV_PATH,
            )
        )

        lesson.rendered_ppt_path = render_result.get("pptx_path")
        lesson.courseware_project_dir = render_result.get("project_dir") or lesson.courseware_project_dir
        lesson.slide_plan_path = render_result.get("slide_plan_path") or lesson.slide_plan_path
        lesson.courseware_render_mode = render_mode
        lesson.narration_paths = json.dumps(narration_result.get("narration_paths") or {}, ensure_ascii=False)
        lesson.courseware_status = "completed"
        lesson.courseware_error = None
        lesson.status = "draft"
        db.commit()
    except Exception as exc:
        logger.exception("Courseware render failed for lesson %s", lesson_id)
        lesson.courseware_status = "failed"
        lesson.courseware_error = str(exc)[:1000]
        lesson.status = "failed"
        db.commit()


def get_workflow_status(db: Session, lesson_id: str) -> Optional[dict]:
    """Build a comprehensive workflow status for a lesson."""
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None:
        return None

    steps: list[dict] = []
    error_msg = None

    parse_task = db.query(ParseTask).filter(ParseTask.parse_id == lesson_id).first()
    if parse_task:
        steps.append(
            {"step": "课件解析", "status": parse_task.task_status, "detail": parse_task.error_message}
        )
        if parse_task.task_status == "failed":
            error_msg = parse_task.error_message
    elif lesson.status == "generating":
        steps.append({"step": "课件解析", "status": "processing"})

    script = None
    if lesson.script_id:
        script = db.query(Script).filter(Script.script_id == lesson.script_id).first()
    if script:
        steps.append({"step": "脚本生成", "status": script.task_status, "detail": script.error_message})
        if script.task_status == "failed":
            error_msg = error_msg or script.error_message
    elif parse_task and parse_task.task_status == "completed":
        steps.append(
            {"step": "脚本生成", "status": "processing" if lesson.status == "generating" else "pending"}
        )

    if lesson.rendered_ppt_path:
        steps.append({"step": "PPT 渲染", "status": "completed"})
    elif script and script.task_status == "completed":
        steps.append(
            {"step": "PPT 渲染", "status": "processing" if lesson.status == "generating" else "pending"}
        )

    if lesson.status == "generating":
        workflow_status = "processing"
    elif lesson.status == "failed":
        workflow_status = "failed"
    else:
        workflow_status = "completed"

    return {
        "lessonId": lesson.lesson_id,
        "lessonName": lesson.lesson_name,
        "workflowStatus": workflow_status,
        "steps": steps,
        "parseId": lesson.parse_id,
        "scriptId": lesson.script_id,
        "renderedPptUrl": f"/api/v1/lesson/download/{lesson.lesson_id}" if lesson.rendered_ppt_path else None,
        "errorMessage": error_msg,
    }


def render_ppt_for_lesson(db: Session, lesson_id: str) -> None:
    """Render PPT for a lesson using stored ppt_outline + parser/script data."""
    from src.schemas import InputAsset, LessonScript, PageBlock, PPTOutline
    from src.utils.renderers import render_ppt_outline

    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None or not lesson.ppt_outline:
        raise ValueError("PPT outline not found for lesson")

    original_status = lesson.status if lesson.status != "rendering" else "draft"
    if original_status != "published":
        lesson.status = "rendering"
        db.commit()

    try:
        ppt_outline = PPTOutline.model_validate(json.loads(lesson.ppt_outline))

        script = db.query(Script).filter(Script.script_id == lesson.script_id).first()
        if script is None or not script.generate_output:
            raise ValueError("Generated script output not found")
        gen_output = json.loads(script.generate_output)
        lesson_script = LessonScript.model_validate(gen_output["lesson_script"])

        parse_task = get_parse_task(db, lesson.parse_id)
        if parse_task is None or not parse_task.parser_output:
            raise ValueError("Parser output not found")
        parser_output = json.loads(parse_task.parser_output)
        source_assets = [InputAsset.model_validate(a) for a in parser_output.get("source_assets", [])]
        source_pages = [PageBlock.model_validate(p) for p in parser_output.get("pages", [])]

        render_dir = Path(settings.RENDER_DIR)
        render_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(render_dir / f"{lesson_id}.pptx")

        rendered_path = render_ppt_outline(
            ppt_outline=ppt_outline,
            lesson_script=lesson_script,
            source_assets=source_assets,
            source_pages=source_pages,
            output_path=output_path,
        )

        lesson.rendered_ppt_path = str(rendered_path)
        lesson.status = original_status
        db.commit()
    except Exception:
        lesson.status = original_status
        db.commit()
        raise


def get_preview_meta(db: Session, lesson_id: str) -> Optional[dict]:
    """Return preview metadata (slide thumbnails, page count, ...) for a lesson.

    Reads the most recent rendered artifact directory under
    ``paths.render_dir`` and combines it with lesson DB metadata.
    """
    from src.utils.renderers import (
        count_presentation_pages,
        render_presentation_preview_image,
    )

    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None:
        return None

    if lesson.rendered_ppt_path:
        rendered_path = Path(lesson.rendered_ppt_path)
        if not rendered_path.exists():
            return {
                "lessonId": lesson_id,
                "taskStatus": "failed",
                "slideCount": 0,
                "renderedPptUrl": None,
                "errorMessage": "Rendered PPT file is missing",
            }

        try:
            slide_count = count_presentation_pages(rendered_path)
        except Exception as exc:
            return {
                "lessonId": lesson_id,
                "taskStatus": "failed",
                "slideCount": 0,
                "renderedPptUrl": None,
                "errorMessage": str(exc),
            }

        if slide_count > 0:
            cache_dir = rendered_path.parent / f"{rendered_path.stem}_assets"
            preview_image, preview_error = render_presentation_preview_image(
                rendered_path,
                1,
                cache_dir,
            )
            if preview_image is None:
                return {
                    "lessonId": lesson_id,
                    "taskStatus": "failed",
                    "slideCount": 0,
                    "renderedPptUrl": None,
                    "errorMessage": preview_error or "Preview image is unavailable",
                }

        return {
            "lessonId": lesson_id,
            "taskStatus": "completed",
            "slideCount": slide_count,
            "renderedPptUrl": f"/api/v1/lesson/download/{lesson.lesson_id}",
            "narrationAudioTasks": get_narration_audio_tasks(db, lesson.lesson_id),
            "errorMessage": None,
        }

    if lesson.status == "rendering":
        return {
            "lessonId": lesson_id,
            "taskStatus": "processing",
            "slideCount": 0,
            "renderedPptUrl": None,
            "errorMessage": None,
        }

    return {
        "lessonId": lesson_id,
        "taskStatus": "failed",
        "slideCount": 0,
        "renderedPptUrl": None,
        "errorMessage": "PPT preview has not been generated yet",
    }


def publish_lesson(
    db: Session,
    lesson_id: str,
    lesson_name: str,
    course_desc: Optional[str] = None,
    tag: Optional[str] = None,
    cover_url: Optional[str] = None,
) -> Optional[Lesson]:
    """Set lesson status to published and update metadata."""
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None:
        return None
    lesson.status = "published"
    resolved_name = (lesson_name or "").strip()
    if resolved_name == "人工智能导论" and lesson.parse_id:
        parse_task = db.query(ParseTask).filter(ParseTask.parse_id == lesson.parse_id).first()
        if parse_task and parse_task.file_name:
            resolved_name = Path(parse_task.file_name).stem or resolved_name
    if resolved_name:
        lesson.lesson_name = resolved_name
    structured_content = {}
    if lesson.structured_content:
        try:
            loaded_content = json.loads(lesson.structured_content)
            if isinstance(loaded_content, dict):
                structured_content = loaded_content
        except json.JSONDecodeError:
            logger.warning("structured_content for lesson %s is not valid JSON; resetting.", lesson.lesson_id)
            structured_content = {}
    publish_meta = structured_content.get("_publishMeta")
    if not isinstance(publish_meta, dict):
        publish_meta = {}
    publish_meta["courseDesc"] = (course_desc or "").strip()
    publish_meta["tag"] = (tag or "").strip()
    publish_meta["coverUrl"] = (cover_url or "").strip()
    structured_content["_publishMeta"] = publish_meta
    lesson.structured_content = json.dumps(structured_content, ensure_ascii=False)
    db.commit()
    db.refresh(lesson)
    return lesson


def archive_lesson(db: Session, lesson_id: str) -> Optional[Lesson]:
    """Hide a lesson from published lists without deleting generated assets."""
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None:
        return None
    lesson.status = "archived"
    db.commit()
    db.refresh(lesson)
    return lesson


def list_lessons(db: Session, status: Optional[str] = None) -> list[dict]:
    """Return lessons ordered by creation time, optionally filtered by status."""
    query = db.query(Lesson)
    if status:
        query = query.filter(Lesson.status == status)
    lessons = query.order_by(Lesson.created_at.desc()).all()

    result = []
    for lesson in lessons:
        script = None
        if lesson.script_id:
            script = db.query(Script).filter(Script.script_id == lesson.script_id).first()
        parse_task = None
        if lesson.parse_id:
            parse_task = db.query(ParseTask).filter(ParseTask.parse_id == lesson.parse_id).first()
        section_count = 0
        if script and script.script_structure:
            try:
                sections = json.loads(script.script_structure)
                section_count = len(sections) if isinstance(sections, list) else 0
            except json.JSONDecodeError:
                logger.debug("script_structure for script %s is not valid JSON", script.script_id)
        audio = get_latest_completed_audio_for_script(db, lesson.script_id or "")
        lesson_name = lesson.lesson_name or lesson.lesson_id
        if lesson_name == "人工智能导论" and parse_task and parse_task.file_name:
            lesson_name = Path(parse_task.file_name).stem or lesson_name
        publish_meta = {}
        if lesson.structured_content:
            try:
                structured_content = json.loads(lesson.structured_content)
                if isinstance(structured_content, dict) and isinstance(
                    structured_content.get("_publishMeta"), dict
                ):
                    publish_meta = structured_content["_publishMeta"]
            except json.JSONDecodeError:
                logger.debug(
                    "structured_content for lesson %s is not valid JSON; skipping publish meta.",
                    lesson.lesson_id,
                )
        result.append(
            {
                "lessonId": lesson.lesson_id,
                "lessonName": lesson_name,
                "tag": publish_meta.get("tag", ""),
                "courseDesc": publish_meta.get("courseDesc", ""),
                "coverUrl": publish_meta.get("coverUrl", ""),
                "status": lesson.status,
                "courseId": lesson.course_id,
                "parseId": lesson.parse_id,
                "scriptId": lesson.script_id,
                "audioId": audio.audio_id if audio else "",
                "audioUrl": audio.audio_url if audio else "",
                "sectionCount": section_count,
                "previewReady": bool(lesson.rendered_ppt_path),
                "renderedPptUrl": f"/api/v1/lesson/download/{lesson.lesson_id}"
                if lesson.rendered_ppt_path
                else None,
                "coursewareStatus": lesson.courseware_status,
                "renderMode": lesson.courseware_render_mode,
                "slidePlanReady": bool(lesson.slide_plan_json),
                "narrationReady": bool(lesson.narration_paths),
                "narrationAudioTasks": get_narration_audio_tasks(db, lesson.lesson_id),
                "createdAt": lesson.created_at.strftime("%Y-%m-%d") if lesson.created_at else "",
            }
        )
    return result


def get_preview_image_path(
    db: Session,
    lesson_id: str,
    slide_number: int,
) -> tuple[Optional[Path], Optional[str]]:
    """Resolve the absolute file path for a single preview image.

    Returns ``None`` if the lesson has no preview artifacts or the
    requested page is out of range.
    """
    from src.utils.renderers import render_presentation_preview_image

    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None:
        return None, "Lesson not found"
    if not lesson.rendered_ppt_path:
        if lesson.status == "rendering":
            return None, "PPT preview is still rendering"
        return None, "PPT preview has not been generated"

    rendered_path = Path(lesson.rendered_ppt_path)
    if not rendered_path.exists():
        return None, "Rendered PPT file is missing"

    cache_dir = rendered_path.parent / f"{rendered_path.stem}_assets"
    return render_presentation_preview_image(rendered_path, slide_number, cache_dir)


# Helpers


def _get_courseware_meta(lesson: Lesson) -> dict:
    if not lesson.structured_content:
        return {}
    try:
        payload = json.loads(lesson.structured_content)
    except json.JSONDecodeError:
        return {}
    meta = payload.get("_courseware") if isinstance(payload, dict) else None
    return meta if isinstance(meta, dict) else {}


def _build_courseware_instruction(*, lesson_name: str, instruction: str) -> str:
    base = instruction.strip()
    if base:
        return base
    return (
        f"请基于上传课件《{lesson_name or '未命名课件'}》生成一份适合课堂教学的 slide_plan.json。"
        "要求内容完整、结构清晰、每页信息密度适中，并保留必要的课堂提问与总结页。"
    )


def _read_json_file(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_slide_plan_payload(slide_plan: dict) -> None:
    if not isinstance(slide_plan, dict):
        raise ValueError("slidePlan must be a JSON object")
    slides = slide_plan.get("slides")
    if not isinstance(slides, list) or not slides:
        raise ValueError("slidePlan.slides must be a non-empty list")
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            raise ValueError(f"slide {index} must be an object")
        if not slide.get("title"):
            raise ValueError(f"slide {index} is missing title")


def _get_file_size(file_url: str) -> int:
    """Return file size in bytes for a local path; 0 if unavailable."""
    if file_url.startswith("http"):
        return 0
    try:
        return os.path.getsize(file_url)
    except OSError:
        return 0


def _download_to_local(url: str, file_type: str) -> str:
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)
    local_path = upload_dir / f"{uuid.uuid4().hex}.{file_type}"
    try:
        urlretrieve(url, str(local_path))
        logger.info("Downloaded %s -> %s", url, local_path)
    except Exception as exc:
        logger.error("Failed to download %s: %s", url, exc)
        raise RuntimeError(f"课件文件下载失败: {exc}") from exc
    return str(local_path)


def _build_structure_preview(sections, pages) -> dict:
    chapters = []
    for sec in sections:
        sub_chapters = []
        for page in pages:
            if page.section_id == sec.section_id or page.page in sec.page_range:
                sub_chapters.append(
                    {
                        "subChapterId": page.page_id or f"page_{page.page}",
                        "subChapterName": page.title or f"Page {page.page}",
                        "isKeyPoint": bool(page.knowledge_points),
                        "pageRange": f"{page.page}",
                    }
                )
        chapters.append(
            {
                "chapterId": sec.section_id,
                "chapterName": sec.name,
                "subChapters": sub_chapters,
            }
        )
    return {"chapters": chapters}


def _build_script_structure(stages: dict) -> list:
    lesson_script = stages.get("lesson_script")
    if lesson_script is None:
        return []
    result = []
    for block in lesson_script.script_blocks:
        char_count = len(block.script_text)
        duration = max(10, int(char_count / 5))
        result.append(
            {
                "sectionId": block.section_id,
                "sectionName": block.title,
                "content": block.script_text,
                "duration": duration,
                "relatedChapterId": block.section_id,
                "keyPoints": list(block.key_points),
            }
        )
    return result


def _ensure_lesson(
    db: Session,
    *,
    lesson_id: str,
    course_id: Optional[str],
    lesson_name: str,
    parse_id: str,
    structured_content: dict,
) -> Lesson:
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    if lesson is None:
        lesson = Lesson(
            lesson_id=lesson_id,
            course_id=course_id,
            parse_id=parse_id,
            lesson_name=lesson_name,
            structured_content=json.dumps(structured_content, ensure_ascii=False),
        )
        db.add(lesson)
    else:
        lesson.structured_content = json.dumps(structured_content, ensure_ascii=False)
        lesson.parse_id = parse_id
    db.flush()
    return lesson


def _format_parse_result(task: ParseTask, structure_preview: dict) -> dict:
    return {
        "parseId": task.parse_id,
        "fileInfo": {
            "fileName": task.file_name,
            "fileSize": task.file_size or 0,
            "pageCount": task.page_count or 0,
        },
        "structurePreview": structure_preview,
        "taskStatus": task.task_status,
    }


def _format_script_result(script: Script, script_structure: list) -> dict:
    return {
        "scriptId": script.script_id,
        "scriptStructure": script_structure,
        "editUrl": f"/script/edit?scriptId={script.script_id}",
        "audioGenerateUrl": "/api/v1/lesson/generateAudio",
    }


def _format_audio_result(audio: AudioTask, section_audios: list) -> dict:
    return {
        "audioId": audio.audio_id,
        "audioUrl": audio.audio_url,
        "audioInfo": {
            "totalDuration": audio.total_duration or 0,
            "fileSize": audio.file_size or 0,
            "format": audio.audio_format,
            "bitRate": audio.bit_rate or 128000,
        },
        "sectionAudios": section_audios,
    }
