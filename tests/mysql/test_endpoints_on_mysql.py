"""Run a representative slice of the API contract against real MySQL.

The aim isn't to re-run the full ``tests/api/`` suite — those already
verified the contract on SQLite.  Here we focus on operations that have
historically broken on MySQL specifically:

* large LONGTEXT round-trip (``structured_content`` in lessons)
* ``ON UPDATE CURRENT_TIMESTAMP`` actually firing on writes
* JSON in TEXT columns surviving an utf8mb4 encode/decode cycle
* uniqueness constraints rejecting duplicate IDs
* foreign-key-like ID references (logical FK; we keep them at the app layer)

Each test uses a unique ID prefix so they can run in any order without
clashing on the unique constraints.
"""

from __future__ import annotations

import json
import time
import uuid


def _uid(prefix: str) -> str:
    """Return a unique-per-test identifier under the requested prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


# ---------------------------------------------------------------------
# Lesson lifecycle
# ---------------------------------------------------------------------


def test_parse_endpoint_writes_to_mysql(client, db):
    """``/lesson/parse`` row must land in MySQL ``parse_tasks`` table."""
    from src.api.models.tables import ParseTask

    school_id = _uid("sch")
    r = client.post(
        "/api/v1/lesson/parse",
        json={
            "schoolId": school_id,
            "userId": "tea_mysql_test",
            "courseId": "cou_mysql_test",
            "fileType": "pdf",
            "fileUrl": "/tmp/fake.pdf",
        },
    )
    assert r.status_code == 200
    parse_id = r.json()["data"]["parseId"]

    db.expire_all()
    row = db.query(ParseTask).filter(ParseTask.parse_id == parse_id).first()
    assert row is not None
    assert row.school_id == school_id
    assert row.task_status == "processing"
    assert row.created_at is not None
    assert row.updated_at is not None


def test_unique_constraint_rejects_duplicate_parse_id(client, db):
    """Inserting two ParseTask rows with the same ``parse_id`` must fail."""
    from src.api.models.tables import ParseTask

    parse_id = _uid("parse")
    db.add(
        ParseTask(
            parse_id=parse_id,
            school_id="sch",
            user_id="u",
            course_id="c",
            file_type="pdf",
            file_url="/tmp/x.pdf",
            file_name="x.pdf",
            task_status="processing",
        )
    )
    db.commit()

    db.add(
        ParseTask(
            parse_id=parse_id,  # duplicate
            school_id="sch2",
            user_id="u2",
            course_id="c2",
            file_type="pdf",
            file_url="/tmp/y.pdf",
            file_name="y.pdf",
            task_status="processing",
        )
    )
    import pytest
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_longtext_round_trip_for_structured_content(client, db):
    """A ~200KB JSON blob round-trips through ``Lesson.structured_content``.

    On a Text column this would silently truncate at 64KB.  LONGTEXT must
    keep the full payload.
    """
    from src.api.models.tables import Lesson

    # Build a ~200KB JSON document.
    big_payload = {
        "lesson_id": "lesson_big",
        "lesson_summary": "x" * 200_000,
        "sections": [{"section_id": f"sec{i}", "name": f"section {i}"} for i in range(10)],
    }
    raw = json.dumps(big_payload, ensure_ascii=False)
    assert len(raw.encode("utf-8")) > 200_000

    lesson_id = _uid("lesson")
    rec = Lesson(
        lesson_id=lesson_id,
        course_id="cou_big",
        lesson_name="超长内容测试",
        status="parsed",
        structured_content=raw,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # Re-read with a fresh query to bypass identity map caching.
    db.expire_all()
    fetched = db.query(Lesson).filter(Lesson.lesson_id == lesson_id).first()
    assert fetched.structured_content == raw, "LONGTEXT round-trip changed bytes"
    parsed = json.loads(fetched.structured_content)
    assert len(parsed["sections"]) == 10


def test_updated_at_advances_on_write(client, db):
    """``ON UPDATE CURRENT_TIMESTAMP`` should bump ``updated_at`` on UPDATE."""
    from src.api.models.tables import Lesson

    lesson_id = _uid("lesson")
    rec = Lesson(
        lesson_id=lesson_id,
        course_id="cou_touch",
        lesson_name="初始名",
        status="parsed",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    first_updated = rec.updated_at
    assert first_updated is not None

    # MySQL DATETIME has 1-second precision by default; sleep just over a
    # second to make sure ``updated_at`` definitely advances.
    time.sleep(1.1)

    rec.lesson_name = "更新后的名"
    db.commit()
    db.refresh(rec)
    second_updated = rec.updated_at

    assert second_updated > first_updated, (
        f"updated_at did not advance: {first_updated} → {second_updated}. "
        "Check that tables.py emits ON UPDATE CURRENT_TIMESTAMP."
    )


# ---------------------------------------------------------------------
# Cross-table: parse → lesson → script → audio
# ---------------------------------------------------------------------


def test_full_lifecycle_persists_correctly(client, db):
    """Smoke: insert a parse + lesson + script + audio quartet and verify
    the rows are wired up the way the API expects them."""
    from src.api.deps import generate_id
    from src.api.models.tables import AudioTask, Lesson, ParseTask, Script

    parse_id = generate_id("parse")
    db.add(
        ParseTask(
            parse_id=parse_id,
            school_id="sch_lc",
            user_id="u_lc",
            course_id="c_lc",
            file_type="pdf",
            file_url="/tmp/x.pdf",
            file_name="lifecycle.pdf",
            task_status="completed",
            page_count=3,
        )
    )
    db.add(
        Lesson(
            lesson_id=parse_id,
            course_id="c_lc",
            lesson_name="lifecycle.pdf",
            status="parsed",
            structured_content=f'{{"lesson_id": "{parse_id}"}}',
        )
    )
    db.commit()

    script_id = generate_id("script")
    db.add(
        Script(
            script_id=script_id,
            parse_id=parse_id,
            lesson_id=parse_id,
            teaching_style="standard",
            speech_speed="normal",
            task_status="completed",
            script_structure='[{"sectionId": "s1", "content": "讲稿"}]',
        )
    )
    db.commit()

    audio_id = generate_id("audio")
    db.add(
        AudioTask(
            audio_id=audio_id,
            script_id=script_id,
            voice_type="female_standard",
            audio_format="mp3",
            task_status="completed",
            total_duration=120,
            file_size=512_000,
        )
    )
    db.commit()

    # Endpoint round-trip
    r = client.post("/api/v1/lesson/parseStatus", json={"parseId": parse_id})
    assert r.status_code == 200
    assert r.json()["data"]["fileInfo"]["pageCount"] == 3

    r = client.post("/api/v1/lesson/scriptStatus", json={"scriptId": script_id})
    assert r.status_code == 200
    assert r.json()["data"]["audioId"] == audio_id  # script joins audio

    r = client.post("/api/v1/lesson/audioStatus", json={"audioId": audio_id})
    assert r.status_code == 200
    assert r.json()["data"]["audioInfo"]["totalDuration"] == 120


# ---------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------


def test_kb_create_persists_to_mysql(client, db):
    from src.api.models.tables import KnowledgeBase

    course_id = _uid("cou_kb")
    r = client.post(
        "/internal/kb/create",
        json={"courseId": course_id, "kbName": "MySQL 测试库", "indexBackend": "numpy"},
    )
    assert r.status_code == 200
    kb_id = r.json()["data"]["kbId"]

    db.expire_all()
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.kb_id == kb_id).first()
    assert kb is not None
    assert kb.kb_name == "MySQL 测试库"
    assert kb.course_id == course_id
    assert kb.index_backend == "numpy"


def test_kb_chunks_table_handles_dense_payload(db):
    """``knowledge_chunks.text`` is LONGTEXT and must accept a big chunk."""
    from src.api.deps import generate_id
    from src.api.models.tables import KnowledgeBase, KnowledgeChunk

    kb_id = generate_id("kb")
    db.add(
        KnowledgeBase(
            kb_id=kb_id,
            course_id="cou_chunks",
            kb_name="chunk-test",
            index_backend="numpy",
            status="ready",
        )
    )
    db.commit()

    # 50KB chunk text — well over the TEXT 64KB risk floor when CJK is involved.
    big_text = "知识点" * 20_000  # 60KB UTF-8
    chunk = KnowledgeChunk(
        chunk_id=generate_id("chunk"),
        kb_id=kb_id,
        lesson_id="lesson_x",
        source_type="page",
        source_id="page_1",
        chunk_index=0,
        text=big_text,
    )
    db.add(chunk)
    db.commit()
    db.refresh(chunk)

    db.expire_all()
    fetched = db.query(KnowledgeChunk).filter(KnowledgeChunk.chunk_id == chunk.chunk_id).first()
    assert fetched.text == big_text


# ---------------------------------------------------------------------
# Progress + platform on real MySQL
# ---------------------------------------------------------------------


def test_progress_track_persists(client, db):
    from src.api.models.tables import LearningProgress

    user_id = _uid("stu")
    r = client.post(
        "/api/v1/progress/track",
        json={
            "schoolId": "sch_p",
            "userId": user_id,
            "courseId": "cou_p",
            "lessonId": "lesson_p",
            "currentSectionId": "sec1",
            "progressPercent": 67.5,
            "lastOperateTime": "2026-05-23 10:00:00",
        },
    )
    assert r.status_code == 200

    db.expire_all()
    rows = db.query(LearningProgress).filter(LearningProgress.user_id == user_id).all()
    assert len(rows) >= 1
    assert any(abs(row.progress_percent - 67.5) < 1e-6 for row in rows)


def test_platform_sync_user_persists(client, db):
    from src.api.models.tables import User

    platform_user_id = _uid("plat_user")
    r = client.post(
        "/api/v1/platform/syncUser",
        json={
            "platformId": "plat001",
            "userInfo": {
                "userId": platform_user_id,  # external platform's id
                "userName": "测试用户·李四",
                "role": "student",
                "schoolId": "sch_sync",
            },
        },
    )
    assert r.status_code == 200
    body = r.json()["data"]
    internal_id = body["internalUserId"]
    assert internal_id  # service generates an internal user_id

    db.expire_all()
    # The external id is stored on platform_user_id, not user_id.
    user = db.query(User).filter(User.platform_user_id == platform_user_id).first()
    assert user is not None
    assert user.user_id == internal_id
    assert "测试用户" in user.user_name
    assert user.platform_id == "plat001"


# ---------------------------------------------------------------------
# QA session
# ---------------------------------------------------------------------


def test_qa_session_idempotent_create(client, db):
    """Two POST /qa/interact with the same sessionId must reuse the row."""
    from src.api.models.tables import QASession

    session_id = _uid("sess")

    # We only care about the session row creation, not the actual agent
    # invocation.  Mock it in process to keep the test fast.
    from src.api.services import qa_service

    original = qa_service.run_qa_interact
    qa_service.run_qa_interact = lambda db, **kw: {  # type: ignore[assignment]
        "answerId": "ans_x",
        "answerContent": "x",
        "answerType": "text",
        "relatedKnowledge": None,
        "suggestions": [],
        "understandingLevel": "partial",
        "questionType": "definition",
        "recommendedNarrationLevel": "B",
        "nextAction": "resume",
        "reason": "",
        "matchedSectionId": None,
        "matchedPage": None,
        "targetSectionId": None,
        "targetPage": None,
    }
    try:
        for _ in range(2):
            r = client.post(
                "/api/v1/qa/interact",
                json={
                    "schoolId": "sch_q",
                    "userId": "stu_q",
                    "courseId": "cou_q",
                    "lessonId": "lesson_q",
                    "sessionId": session_id,
                    "questionContent": "what?",
                },
            )
            assert r.status_code == 200
    finally:
        qa_service.run_qa_interact = original

    db.expire_all()
    rows = db.query(QASession).filter(QASession.session_id == session_id).all()
    assert len(rows) == 1
