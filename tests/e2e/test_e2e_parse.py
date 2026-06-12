"""E2E phase 1: real PDF parsing.

Drives the parse pipeline end-to-end:

    POST /api/v1/lesson/parse  →  ``ParseTask`` row in DB
    run_parse_task(...)        →  PyMuPDF parse + LLM structuring
    POST /api/v1/lesson/parseStatus  →  ``completed`` payload

The LLM call is real (uses ``.env``).  When the LLM is unreachable, the
parser falls back to its baseline structured content, which still
results in ``task_status == "completed"`` — we only assert on that
contract, not on the *quality* of structured content.

Successful artifacts:

* ``ParseTask.task_status == "completed"``
* ``ParseTask.page_count >= 1``
* ``Lesson`` row mirrors the parse_id
* ``Lesson.structured_content`` is valid JSON with sections / pages
"""

from __future__ import annotations

import json
import time

import pytest

pytestmark = pytest.mark.e2e


def test_parse_real_pdf_completes(client, db, tiny_pdf):
    """Submit a real PDF and drive the parse pipeline synchronously."""
    from src.api.models.tables import Lesson, ParseTask
    from src.api.services import lesson_service

    # Step 1: create the parse task (router path)
    r = client.post(
        "/api/v1/lesson/parse",
        json={
            "schoolId": "sch_e2e",
            "userId": "tea_e2e",
            "courseId": "cou_e2e_parse",
            "fileType": "pdf",
            "fileUrl": str(tiny_pdf),
            "isExtractKeyPoint": True,
        },
    )
    assert r.status_code == 200, r.text
    parse_id = r.json()["data"]["parseId"]
    assert parse_id.startswith("parse")

    # Step 2: drive the actual pipeline (BackgroundTasks were short-circuited).
    task = db.query(ParseTask).filter(ParseTask.parse_id == parse_id).first()
    assert task is not None
    assert task.task_status == "processing"

    started = time.monotonic()
    result = lesson_service.run_parse_task(db, task)
    elapsed = time.monotonic() - started
    print(f"\n  parse pipeline elapsed: {elapsed:.1f}s")

    # Step 3: contract assertions
    db.refresh(task)
    assert task.task_status == "completed", (
        f"parse failed: {task.error_message!r} (check .env LLM_* keys; baseline fallback should still pass)"
    )
    assert task.page_count >= 1
    assert result.get("taskStatus") == "completed"

    lesson = db.query(Lesson).filter(Lesson.lesson_id == parse_id).first()
    assert lesson is not None, "Lesson row should be created during parse"
    assert lesson.structured_content, "structured_content must be populated"

    structured = json.loads(lesson.structured_content)
    assert structured.get("lesson_id") == parse_id
    assert isinstance(structured.get("pages"), list)
    assert isinstance(structured.get("sections"), list)
    assert len(structured["pages"]) >= 1


def test_parse_status_after_run(client, db, tiny_pdf):
    """End-to-end: create → run → poll status, all via HTTP."""
    from src.api.models.tables import ParseTask
    from src.api.services import lesson_service

    r = client.post(
        "/api/v1/lesson/parse",
        json={
            "schoolId": "sch_e2e",
            "userId": "tea_e2e",
            "courseId": "cou_e2e_status",
            "fileType": "pdf",
            "fileUrl": str(tiny_pdf),
        },
    )
    parse_id = r.json()["data"]["parseId"]

    task = db.query(ParseTask).filter(ParseTask.parse_id == parse_id).first()
    lesson_service.run_parse_task(db, task)

    # Now query via the public status endpoint.
    poll = client.post("/api/v1/lesson/parseStatus", json={"parseId": parse_id})
    assert poll.status_code == 200
    body = poll.json()["data"]
    assert body["taskStatus"] == "completed"
    assert body["fileInfo"]["pageCount"] >= 1
    assert body["fileInfo"]["fileName"]
    # structurePreview should be populated by the parser.
    assert body["structurePreview"]


def test_parse_invalid_path_marks_task_failed(client, db, tmp_path):
    """A non-existent file should mark the task ``failed`` with a message."""
    from src.api.models.tables import ParseTask
    from src.api.services import lesson_service

    bogus = tmp_path / "does_not_exist.pdf"  # path that won't resolve

    r = client.post(
        "/api/v1/lesson/parse",
        json={
            "schoolId": "sch_e2e",
            "userId": "tea_e2e",
            "courseId": "cou_e2e_fail",
            "fileType": "pdf",
            "fileUrl": str(bogus),
        },
    )
    parse_id = r.json()["data"]["parseId"]

    task = db.query(ParseTask).filter(ParseTask.parse_id == parse_id).first()
    lesson_service.run_parse_task(db, task)

    db.refresh(task)
    assert task.task_status == "failed"
    assert task.error_message
