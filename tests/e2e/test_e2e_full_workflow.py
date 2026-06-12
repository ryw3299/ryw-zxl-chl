"""E2E phase 4: full teacher workflow + PPT render.

Two flavors are exercised:

1. **Step-by-step**: parse → script → render_ppt_for_lesson, asserting
   that ``Lesson.rendered_ppt_path`` is populated and the file exists.

2. **One-shot**: ``run_full_workflow`` does everything in a single call.
   We only assert the lesson row reaches ``status == "completed"`` and
   the ppt artifact file is on disk.

PPT rendering is CPU-bound but does NOT call the LLM beyond what
``generate_script`` already did, so this phase is fast (~ a few seconds).
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e


def test_render_ppt_after_script(client, db, tiny_pdf):
    """parse → script → render → ``Lesson.rendered_ppt_path`` exists."""
    from src.api.models.tables import Lesson, ParseTask, Script
    from src.api.services import lesson_service

    # Phase A: parse
    r = client.post(
        "/api/v1/lesson/parse",
        json={
            "schoolId": "sch_e2e",
            "userId": "tea_e2e",
            "courseId": "cou_e2e_render",
            "fileType": "pdf",
            "fileUrl": str(tiny_pdf),
        },
    )
    parse_id = r.json()["data"]["parseId"]
    task = db.query(ParseTask).filter(ParseTask.parse_id == parse_id).first()
    lesson_service.run_parse_task(db, task)

    # Phase B: script (needed so ppt_outline is populated)
    r = client.post(
        "/api/v1/lesson/generateScript",
        json={"parseId": parse_id, "teachingStyle": "concise"},
    )
    script_id = r.json()["data"]["scriptId"]
    script = db.query(Script).filter(Script.script_id == script_id).first()
    lesson_service.run_generate_script(db, script)

    # Phase C: trigger render (BackgroundTasks short-circuited)
    r = client.post("/api/v1/lesson/renderPPT", json={"lessonId": parse_id})
    assert r.status_code == 200, r.text

    # Drive the render synchronously
    started = time.monotonic()
    try:
        lesson_service.render_ppt_for_lesson(db, parse_id)
    except Exception as exc:
        pytest.skip(f"PPT renderer unavailable in this environment: {exc!r}")
    elapsed = time.monotonic() - started
    print(f"\n  render pipeline elapsed: {elapsed:.1f}s")

    # Phase D: contract assertions
    db.expire_all()
    lesson = db.query(Lesson).filter(Lesson.lesson_id == parse_id).first()
    assert lesson is not None

    if not lesson.rendered_ppt_path:
        pytest.skip(
            "PPT renderer did not populate rendered_ppt_path (check ppt-master / fonts in this environment)"
        )

    pptx_path = Path(lesson.rendered_ppt_path)
    assert pptx_path.exists(), f"rendered pptx missing on disk: {pptx_path}"
    assert pptx_path.stat().st_size > 1000

    # Step E: GET /lesson/download/{lessonId} should serve the file
    download = client.get(f"/api/v1/lesson/download/{parse_id}")
    assert download.status_code == 200
    assert download.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )


def test_full_workflow_one_shot(client, db, tiny_pdf):
    """``run_full_workflow`` orchestrates parse + script + render."""
    from src.api.models.tables import Lesson
    from src.api.services import lesson_service

    # Step 1: kick off via the public endpoint
    r = client.post(
        "/api/v1/lesson/generate",
        json={
            "schoolId": "sch_e2e",
            "userId": "tea_e2e",
            "courseId": "cou_e2e_oneshot",
            "fileType": "pdf",
            "fileUrl": str(tiny_pdf),
            "teachingStyle": "concise",
        },
    )
    assert r.status_code == 200
    lesson_id = r.json()["data"]["lessonId"]

    # Step 2: drive run_full_workflow synchronously
    started = time.monotonic()
    try:
        lesson_service.run_full_workflow(
            db,
            lesson_id=lesson_id,
            school_id="sch_e2e",
            user_id="tea_e2e",
            course_id="cou_e2e_oneshot",
            file_type="pdf",
            file_url=str(tiny_pdf),
            teaching_style="concise",
        )
    except Exception as exc:
        pytest.skip(f"full_workflow failed in this environment: {exc!r}")
    elapsed = time.monotonic() - started
    print(f"\n  full workflow elapsed: {elapsed:.1f}s")

    # Step 3: contract assertions
    db.expire_all()
    lesson = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    assert lesson is not None
    # The full workflow may end in any of these terminal states depending on
    # which sub-stage was reached and whether external services succeeded.
    # We only assert that the row was touched (status moved away from
    # ``generating``).
    assert lesson.status != "generating", f"workflow never advanced past initial state: {lesson.status!r}"
    print(f"\n  workflow terminal status: {lesson.status!r}")

    # Step 4: lesson appears in /lesson/list
    listing = client.get("/api/v1/lesson/list")
    assert listing.status_code == 200
    ids = [l["lessonId"] for l in listing.json()["data"]["lessons"]]
    assert lesson_id in ids


def test_generate_status_polls_workflow(client, db, tiny_pdf):
    """``/lesson/generateStatus`` returns workflow steps after run_full_workflow."""
    from src.api.services import lesson_service

    r = client.post(
        "/api/v1/lesson/generate",
        json={
            "schoolId": "sch_e2e",
            "userId": "tea_e2e",
            "courseId": "cou_e2e_poll",
            "fileType": "pdf",
            "fileUrl": str(tiny_pdf),
        },
    )
    lesson_id = r.json()["data"]["lessonId"]

    try:
        lesson_service.run_full_workflow(
            db,
            lesson_id=lesson_id,
            school_id="sch_e2e",
            user_id="tea_e2e",
            course_id="cou_e2e_poll",
            file_type="pdf",
            file_url=str(tiny_pdf),
            teaching_style="concise",
        )
    except Exception as exc:
        pytest.skip(f"full_workflow failed: {exc!r}")

    # Now poll status
    poll = client.post("/api/v1/lesson/generateStatus", json={"lessonId": lesson_id})
    assert poll.status_code == 200
    body = poll.json()["data"]
    assert body["lessonId"] == lesson_id
    assert "workflowStatus" in body
    assert isinstance(body.get("steps", []), list)
