"""E2E phase 2: real script generation.

Drives the generate-script pipeline against a freshly-parsed lesson:

    Phase A: run_parse_task → completed
    Phase B: POST /api/v1/lesson/generateScript → Script row
             run_generate_script → narration text + ppt_outline
    Phase C: POST /api/v1/lesson/scriptStatus → completed payload

The pipeline calls the LLM multiple times (one per section) so this test
is the most expensive in the e2e suite.  We use ``tiny_pdf`` with one
section to keep token usage minimal.
"""

from __future__ import annotations

import json
import time

import pytest

pytestmark = pytest.mark.e2e


def _seed_completed_parse(client, db, tiny_pdf, course_suffix: str) -> str:
    """Helper: drive a parse to completion and return ``parse_id``."""
    from src.api.models.tables import ParseTask
    from src.api.services import lesson_service

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
    assert task.task_status == "completed", f"prerequisite parse failed: {task.error_message}"
    return parse_id


def test_generate_script_completes(client, db, tiny_pdf):
    """End-to-end: parse a PDF, then generate the narration script."""
    from src.api.models.tables import Lesson, Script
    from src.api.services import lesson_service

    parse_id = _seed_completed_parse(client, db, tiny_pdf, "script")

    # Step 1: create the script via the public endpoint
    r = client.post(
        "/api/v1/lesson/generateScript",
        json={
            "parseId": parse_id,
            "teachingStyle": "concise",  # cheaper to generate than "detailed"
            "speechSpeed": "normal",
        },
    )
    assert r.status_code == 200, r.text
    script_id = r.json()["data"]["scriptId"]
    assert script_id.startswith("script")

    # Step 2: drive the actual pipeline (real LLM)
    script = db.query(Script).filter(Script.script_id == script_id).first()
    started = time.monotonic()
    lesson_service.run_generate_script(db, script)
    elapsed = time.monotonic() - started
    print(f"\n  script pipeline elapsed: {elapsed:.1f}s")

    # Step 3: contract assertions
    db.refresh(script)
    assert script.task_status == "completed", f"script generation failed: {script.error_message!r}"
    assert script.lesson_id == parse_id
    assert script.script_structure

    structure = json.loads(script.script_structure)
    assert isinstance(structure, list)
    assert len(structure) >= 1
    # The first section should have non-empty narration content.
    first = structure[0]
    assert first.get("sectionId")
    assert first.get("content") or first.get("narration"), (
        "script structure entries must carry narration text"
    )

    # Step 4: lesson row should now have a ppt_outline (used by /renderPPT).
    lesson = db.query(Lesson).filter(Lesson.lesson_id == parse_id).first()
    assert lesson is not None
    assert lesson.ppt_outline, "ppt_outline should be persisted alongside the script"


def test_script_status_after_run(client, db, tiny_pdf):
    """Public ``/scriptStatus`` reflects the synchronous run."""
    from src.api.models.tables import Script
    from src.api.services import lesson_service

    parse_id = _seed_completed_parse(client, db, tiny_pdf, "script_status")

    r = client.post(
        "/api/v1/lesson/generateScript",
        json={"parseId": parse_id, "teachingStyle": "concise"},
    )
    script_id = r.json()["data"]["scriptId"]
    script = db.query(Script).filter(Script.script_id == script_id).first()
    lesson_service.run_generate_script(db, script)

    poll = client.post("/api/v1/lesson/scriptStatus", json={"scriptId": script_id})
    assert poll.status_code == 200
    body = poll.json()["data"]
    assert body["taskStatus"] == "completed"
    assert body["scriptId"] == script_id
    assert body["lessonId"] == parse_id
    assert isinstance(body["scriptStructure"], list)
    assert len(body["scriptStructure"]) >= 1


def test_generate_script_rejects_uncompleted_parse(client, db, tiny_pdf):
    """A processing-state parse cannot be promoted to script generation."""
    from src.api.models.tables import ParseTask

    # Create a parse in ``processing`` state without running it.
    r = client.post(
        "/api/v1/lesson/parse",
        json={
            "schoolId": "sch_e2e",
            "userId": "tea_e2e",
            "courseId": "cou_e2e_block",
            "fileType": "pdf",
            "fileUrl": str(tiny_pdf),
        },
    )
    parse_id = r.json()["data"]["parseId"]

    task = db.query(ParseTask).filter(ParseTask.parse_id == parse_id).first()
    assert task.task_status == "processing"  # background task disabled

    # Now try to generate script — router should refuse with 400.
    r2 = client.post(
        "/api/v1/lesson/generateScript",
        json={"parseId": parse_id},
    )
    assert r2.status_code == 400
    assert "wait until it completes" in r2.json()["msg"].lower() or "processing" in r2.text
