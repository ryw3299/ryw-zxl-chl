"""Shared pytest fixtures for API endpoint tests.

Design goals
------------
* **Hermetic**: every test gets a fresh in-memory SQLite database — your real
  MySQL is never touched.
* **Fast**: < 10 s for the full API suite by mocking out LLM / TTS / ASR /
  PPT-render heavy dependencies and short-circuiting ``BackgroundTasks``.
* **Composable**: fixtures expose primitives (``client``, ``db``,
  ``seeded_lesson``, etc.) so individual tests stay short.

Usage in a test file::

    def test_something(client):
        r = client.post("/api/v1/...", json={...})
        assert r.status_code == 200
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

# Configure the test database BEFORE any project module is imported, so
# database.py picks up the SQLite URL on its first build.
_TEST_DB_PATH = Path(__file__).resolve().parent / "_tmp_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ["DEBUG"] = "true"
os.environ["STUDENT_AGENT_BACKEND"] = "claude"  # default; tests don't actually call the agent

# Ensure the project root is importable (mirrors top-level conftest.py)
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------
# Database lifecycle
# ---------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _reset_test_db() -> Generator[None, None, None]:
    """Fresh SQLite for the whole API test session.

    The DB file is deleted on entry/exit so reruns are deterministic.
    """
    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()
    yield
    if _TEST_DB_PATH.exists():
        try:
            _TEST_DB_PATH.unlink()
        except OSError:
            pass


@pytest.fixture(scope="session")
def app():
    """Build the FastAPI app once per test session, against the test DB.

    We rebuild the SQLAlchemy engine here because earlier non-API tests in
    the same pytest session may already have created an engine pointing at
    the production MySQL.  Without rebuilding, ``init_db()`` would commit
    against the wrong database (or fail because the driver is missing).
    """
    from src.api.config import settings

    object.__setattr__(settings, "DATABASE_URL", os.environ["DATABASE_URL"])
    object.__setattr__(settings, "DEBUG", True)

    # Force-rebuild the engine so it picks up the patched DATABASE_URL.
    from src.api.models import database as _db_mod

    new_engine = _db_mod._build_engine_with_url(settings.DATABASE_URL)
    _db_mod.engine = new_engine
    from sqlalchemy.orm import sessionmaker

    _db_mod.SessionLocal = sessionmaker(bind=new_engine, autocommit=False, autoflush=False)

    from src.api.app import app as fastapi_app

    _db_mod.init_db()
    return fastapi_app


@pytest.fixture()
def client(app):
    """A configured ``TestClient`` for the FastAPI app."""
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db(app):
    """Yield a SQLAlchemy session bound to the test DB.

    Depends on ``app`` so the engine has already been rebuilt to point at
    the test SQLite file.
    """
    from src.api.models.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------
# Background-task short-circuit
# ---------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _disable_background_tasks(monkeypatch):
    """Replace ``BackgroundTasks.add_task`` with a no-op.

    The lesson router enqueues parse / script / audio / render in the
    background — those touch the LLM and the filesystem.  For API-level
    contract tests we only care that the request returns a synchronous
    202-style payload, so the no-op keeps tests fast and deterministic.
    """
    from fastapi import BackgroundTasks

    monkeypatch.setattr(BackgroundTasks, "add_task", lambda self, *a, **kw: None)


# ---------------------------------------------------------------------
# Seed factories
# ---------------------------------------------------------------------


@pytest.fixture()
def seeded_parse_task(db) -> Any:
    """Insert a ``ParseTask`` row in ``completed`` state and return it."""
    from src.api.deps import generate_id
    from src.api.models.tables import Lesson, ParseTask

    parse_id = generate_id("parse")
    structured = {
        "lesson_id": parse_id,
        "lesson_title": "测试课时",
        "lesson_summary": "用于 API 测试的占位课时。",
        "sections": [
            {
                "section_id": "sec1",
                "name": "第一节",
                "title": "牛顿第一定律",
                "summary": "惯性参考系的概念。",
                "knowledge_points": ["惯性"],
                "key_points": ["牛顿第一定律"],
                "page_ids": ["p1"],
            }
        ],
        "pages": [
            {
                "page_id": "p1",
                "section_id": "sec1",
                "page_number": 1,
                "title": "牛顿第一定律",
                "content": "物体保持静止或匀速直线运动状态。",
                "summary": "惯性定律。",
                "knowledge_points": ["惯性"],
                "key_points": ["惯性参考系"],
            }
        ],
        "knowledge_points": ["惯性"],
    }

    task = ParseTask(
        parse_id=parse_id,
        school_id="sch_test",
        user_id="tea_test",
        course_id="cou_test",
        file_type="pdf",
        file_url="/tmp/fake.pdf",
        file_name="fake.pdf",
        file_size=1024,
        page_count=1,
        task_status="completed",
        structure_preview=json.dumps({"sectionCount": 1, "pageCount": 1}, ensure_ascii=False),
    )
    db.add(task)

    # Mirror the lesson row that the parse task implicitly seeds.
    lesson = Lesson(
        lesson_id=parse_id,
        course_id="cou_test",
        lesson_name="测试课时",
        status="parsed",
        structured_content=json.dumps(structured, ensure_ascii=False),
    )
    db.add(lesson)
    db.commit()
    db.refresh(task)
    return task


@pytest.fixture()
def seeded_script(db, seeded_parse_task) -> Any:
    """Insert a completed ``Script`` row tied to ``seeded_parse_task``."""
    from src.api.deps import generate_id
    from src.api.models.tables import Script

    script = Script(
        script_id=generate_id("script"),
        parse_id=seeded_parse_task.parse_id,
        lesson_id=seeded_parse_task.parse_id,
        teaching_style="standard",
        speech_speed="normal",
        task_status="completed",
        script_structure=json.dumps(
            [
                {
                    "sectionId": "sec1",
                    "title": "第一节",
                    "narration": "本节讲解牛顿第一定律。",
                }
            ],
            ensure_ascii=False,
        ),
    )
    db.add(script)
    db.commit()
    db.refresh(script)
    return script


@pytest.fixture()
def seeded_audio_task(db, seeded_script) -> Any:
    """Insert a completed ``AudioTask`` row tied to ``seeded_script``."""
    from src.api.deps import generate_id
    from src.api.models.tables import AudioTask

    audio = AudioTask(
        audio_id=generate_id("audio"),
        script_id=seeded_script.script_id,
        voice_type="female_standard",
        audio_format="mp3",
        task_status="completed",
        audio_url="/audio/test.mp3",
        total_duration=120,
        file_size=1_024_000,
        bit_rate=128_000,
        section_audios=json.dumps(
            [{"sectionId": "sec1", "audioUrl": "/audio/test/sec1.mp3", "duration": 60}],
            ensure_ascii=False,
        ),
    )
    db.add(audio)
    db.commit()
    db.refresh(audio)
    return audio


@pytest.fixture()
def seeded_kb(db) -> Any:
    """Insert a ``KnowledgeBase`` row in ``ready`` state.

    Uses a distinct ``course_id`` from ``seeded_parse_task`` so the kb-build
    fallback (which scans lessons by course_id) does not accidentally pick
    up unrelated test lessons.
    """
    from src.api.deps import generate_id
    from src.api.models.tables import KnowledgeBase

    kb = KnowledgeBase(
        kb_id=generate_id("kb"),
        course_id="cou_test_kb_isolated",
        kb_name="API 测试知识库",
        index_backend="numpy",
        status="ready",
        chunk_count=10,
        source_count=1,
    )
    db.add(kb)
    db.commit()
    db.refresh(kb)
    return kb


# ---------------------------------------------------------------------
# External-service mocks
# ---------------------------------------------------------------------


@pytest.fixture()
def mock_voice_to_text(monkeypatch):
    """Stub ``qa_service.voice_to_text`` so ASR network calls don't happen."""
    from src.api.services import qa_service

    def _fake(*, voice_url: str, language: str = "zh-CN") -> dict[str, Any]:
        return {"text": "这是一个测试语音转文字", "confidence": 0.99}

    monkeypatch.setattr(qa_service, "voice_to_text", _fake)
    return _fake


@pytest.fixture()
def mock_run_qa_interact(monkeypatch):
    """Stub the heavy QA-agent call so /qa/interact stays hermetic."""
    from src.api.services import qa_service

    def _fake(db, **_) -> dict[str, Any]:
        return {
            "answerId": "ans_test_001",
            "answerContent": "这是一个测试回答。",
            "answerType": "text",
            "relatedKnowledge": None,
            "suggestions": ["相关问题1", "相关问题2"],
            "understandingLevel": "partial",
            "questionType": "definition",
            "recommendedNarrationLevel": "B",
            "nextAction": "resume",
            "reason": "测试原因",
            "matchedSectionId": "sec1",
            "matchedPage": 1,
            "targetSectionId": "sec1",
            "targetPage": 1,
        }

    monkeypatch.setattr(qa_service, "run_qa_interact", _fake)
    return _fake
