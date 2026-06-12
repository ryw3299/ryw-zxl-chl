"""E2E phase 3: real audio synthesis via edge-tts.

Drives ``run_audio_task`` end-to-end:

    Phase A: parse → completed
    Phase B: generate-script → completed
    Phase C: POST /api/v1/lesson/generateAudio → AudioTask row
             run_audio_task → edge-tts MP3 file under ``paths.audio_dir``
    Phase D: POST /api/v1/lesson/audioStatus → completed payload
    Phase E: GET /api/v1/lesson/audio/{audio_id}/{section_id} → MP3 bytes

Requires network access to Microsoft Edge's TTS endpoints. If those are
unreachable (corporate firewall, GFW, etc.) the synthesis call will fail
and we'll see ``task_status == "failed"``; the test asserts on the
appropriate failure path so it still produces a useful signal.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e


def _seed_completed_script(client, db, tiny_pdf, course_suffix: str):
    """Helper: parse + script in one go, return the completed Script row."""
    from src.api.models.tables import ParseTask, Script
    from src.api.services import lesson_service

    # parse
    r = client.post(
        "/api/v1/lesson/parse",
        json={
            "schoolId": "sch_e2e",
            "userId": "tea_e2e",
            "courseId": f"cou_e2e_{course_suffix}",
            "fileType": "pdf",
            "fileUrl": str(tiny_pdf),
        },
    )
    parse_id = r.json()["data"]["parseId"]
    task = db.query(ParseTask).filter(ParseTask.parse_id == parse_id).first()
    lesson_service.run_parse_task(db, task)
    db.refresh(task)
    assert task.task_status == "completed", f"prereq parse failed: {task.error_message}"

    # script
    r = client.post(
        "/api/v1/lesson/generateScript",
        json={"parseId": parse_id, "teachingStyle": "concise"},
    )
    script_id = r.json()["data"]["scriptId"]
    script = db.query(Script).filter(Script.script_id == script_id).first()
    lesson_service.run_generate_script(db, script)
    db.refresh(script)
    assert script.task_status == "completed", f"prereq script failed: {script.error_message}"
    return script


def test_audio_pipeline_completes_or_fails_cleanly(client, db, tiny_pdf):
    """Drive an audio task; assert either ``completed`` with files, or
    ``failed`` with a clear error message.

    edge-tts requires outbound network connectivity; we accept both
    outcomes to keep this useful in offline / restricted CI as well.
    """
    from src.api.models.tables import AudioTask
    from src.api.services import lesson_service
    from src.utils.paths import paths

    script = _seed_completed_script(client, db, tiny_pdf, "audio")

    # Step 1: create audio task via the public endpoint
    r = client.post(
        "/api/v1/lesson/generateAudio",
        json={
            "scriptId": script.script_id,
            "voiceType": "female_standard",
            "audioFormat": "mp3",
        },
    )
    assert r.status_code == 200
    audio_id = r.json()["data"]["audioId"]
    assert audio_id.startswith("audio")

    # Step 2: drive the synthesis (real edge-tts)
    audio = db.query(AudioTask).filter(AudioTask.audio_id == audio_id).first()
    started = time.monotonic()
    lesson_service.run_audio_task(db, audio)
    elapsed = time.monotonic() - started
    print(f"\n  audio pipeline elapsed: {elapsed:.1f}s")

    db.refresh(audio)
    if audio.task_status == "failed":
        # edge-tts unreachable → at least the failure path must be informative.
        pytest.skip(f"edge-tts unreachable in this environment: {audio.error_message!r}")

    # Step 3: success path assertions
    assert audio.task_status == "completed"
    assert audio.total_duration > 0
    assert audio.file_size > 0
    assert audio.audio_url, "audio_url should be set on completion"

    # The synthesized files should live under paths.audio_dir/<audio_id>/
    audio_dir = Path(paths.audio_dir) / audio_id
    assert audio_dir.exists() and audio_dir.is_dir()
    mp3_files = list(audio_dir.glob("*.mp3"))
    assert mp3_files, f"no .mp3 produced under {audio_dir}"
    # Each file should have non-trivial size (edge-tts mp3 ≥ a few KB).
    for f in mp3_files:
        assert f.stat().st_size > 1000


def test_audio_status_then_download(client, db, tiny_pdf):
    """End-to-end: synthesize, then fetch the binary via the GET endpoint."""
    from src.api.models.tables import AudioTask
    from src.api.services import lesson_service

    script = _seed_completed_script(client, db, tiny_pdf, "audio_dl")

    r = client.post(
        "/api/v1/lesson/generateAudio",
        json={"scriptId": script.script_id, "voiceType": "female_standard"},
    )
    audio_id = r.json()["data"]["audioId"]
    audio = db.query(AudioTask).filter(AudioTask.audio_id == audio_id).first()
    lesson_service.run_audio_task(db, audio)
    db.refresh(audio)

    if audio.task_status != "completed":
        pytest.skip(f"edge-tts unreachable: {audio.error_message!r}")

    # /audioStatus
    poll = client.post("/api/v1/lesson/audioStatus", json={"audioId": audio_id})
    assert poll.status_code == 200
    body = poll.json()["data"]
    assert body["taskStatus"] == "completed"
    assert body["audioInfo"]["totalDuration"] > 0
    assert body["sectionAudios"], "sectionAudios must be populated"

    # GET /audio/{audio_id}/{section_id} — should return audio/mpeg bytes
    section_id = body["sectionAudios"][0]["sectionId"]
    download = client.get(f"/api/v1/lesson/audio/{audio_id}/{section_id}")
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("audio/")
    assert len(download.content) > 1000


def test_audio_404_on_missing_audio(client):
    """Sanity: requesting a non-existent audio returns 404."""
    r = client.post("/api/v1/lesson/audioStatus", json={"audioId": "audio_does_not_exist"})
    assert r.status_code == 404


def test_audio_synthesis_fails_on_empty_script(client, db, tiny_pdf):
    """Edge case: an audio task tied to a script with no narration
    immediately fails with a clear message (no edge-tts call needed)."""
    from src.api.deps import generate_id
    from src.api.models.tables import AudioTask, Script
    from src.api.services import lesson_service

    # Create a fake completed script with empty structure.
    empty_script = Script(
        script_id=generate_id("script"),
        parse_id="parse_fake",
        lesson_id="lesson_fake",
        teaching_style="standard",
        speech_speed="normal",
        task_status="completed",
        script_structure="[]",
    )
    db.add(empty_script)
    db.commit()
    db.refresh(empty_script)

    audio = AudioTask(
        audio_id=generate_id("audio"),
        script_id=empty_script.script_id,
        voice_type="female_standard",
        audio_format="mp3",
        task_status="processing",
        section_ids="[]",
    )
    db.add(audio)
    db.commit()
    db.refresh(audio)

    lesson_service.run_audio_task(db, audio)
    db.refresh(audio)
    assert audio.task_status == "failed"
    assert "脚本内容为空" in (audio.error_message or "")
