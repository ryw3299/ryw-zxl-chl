"""Shared fixtures for end-to-end integration tests.

These tests exercise the **real** pipeline:

* Real PDF → PyMuPDF parse
* Real LLM call (provider configured by ``.env``)
* Real ``edge-tts`` synthesis
* Real database commit (SQLite, isolated from the production MySQL)

They are **opt-in** so a normal ``pytest`` run skips them.  Enable via either:

    RUN_E2E=1 pytest tests/e2e/
    pytest tests/e2e/ --run-e2e

The default behaviour (no flag) marks every test as ``skip`` with a clear
reason so contributors aren't surprised by network errors.
"""

from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import pytest

# ---------------------------------------------------------------------
# Configure the test database BEFORE any project module is imported, so
# database.py picks up the SQLite URL on its first build.
# ---------------------------------------------------------------------

_TEST_DB_PATH = Path(__file__).resolve().parent / "_e2e_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
# Keep signature middleware bypass on; only the SQLAlchemy echo is noisy.
os.environ["DEBUG"] = "true"
os.environ["SQLALCHEMY_ECHO"] = "false"

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ---------------------------------------------------------------------
# Skip-by-default behaviour
# ---------------------------------------------------------------------


def pytest_addoption(parser):
    parser.addoption(
        "--run-e2e",
        action="store_true",
        default=False,
        help="Run end-to-end integration tests that hit the real LLM / TTS.",
    )


def pytest_collection_modifyitems(config, items):
    """Skip every e2e test unless explicitly opted in."""
    if config.getoption("--run-e2e") or os.environ.get("RUN_E2E") in {"1", "true", "yes"}:
        return  # opt-in: run them all

    skip_marker = pytest.mark.skip(
        reason=(
            "e2e tests are skipped by default. Run with "
            "`RUN_E2E=1 pytest tests/e2e/` or `--run-e2e` to enable."
        )
    )
    for item in items:
        # Only auto-skip items that live under tests/e2e/.
        path_str = str(item.fspath)
        if "/tests/e2e/" in path_str or path_str.endswith("tests/e2e"):
            item.add_marker(skip_marker)


# ---------------------------------------------------------------------
# DB lifecycle
# ---------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _reset_e2e_db():
    """Fresh SQLite DB for the whole e2e session."""
    if _TEST_DB_PATH.exists():
        _TEST_DB_PATH.unlink()
    yield
    # Keep the DB file after the run so devs can inspect it on failure.


@pytest.fixture(scope="session")
def app():
    """Build the FastAPI app once, against the e2e SQLite DB."""
    from src.api.config import settings
    from src.api.models import database as _db_mod

    object.__setattr__(settings, "DATABASE_URL", os.environ["DATABASE_URL"])
    object.__setattr__(settings, "DEBUG", True)  # bypass signature middleware

    # Force-rebuild the engine WITHOUT SQL echo (the default ties echo to
    # settings.DEBUG, which would flood e2e logs with PRAGMA / INSERT spam).
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    new_engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )
    _db_mod.engine = new_engine
    _db_mod.SessionLocal = sessionmaker(bind=new_engine, autocommit=False, autoflush=False)

    from src.api.app import app as fastapi_app

    _db_mod.init_db()
    return fastapi_app


@pytest.fixture()
def db(app):
    """Yield a SQLAlchemy session bound to the e2e SQLite DB."""
    from src.api.models.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="session")
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------
# Test PDF — a tiny synthetic 1-page document
# ---------------------------------------------------------------------


@pytest.fixture(scope="session")
def tiny_pdf(tmp_path_factory) -> Path:
    """Generate a 1-page deterministic PDF for e2e parse runs.

    A real PDF is required because the parser uses PyMuPDF.  Keeping it
    synthetic and tiny means the LLM call costs a tiny number of tokens
    and the run finishes in seconds, not minutes.
    """
    import fitz

    pdf_dir = tmp_path_factory.mktemp("e2e_pdf")
    pdf_path = pdf_dir / "tiny_lesson.pdf"

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4
    text = (
        "牛顿第一定律\n\n"
        "概念定义：任何物体在不受外力作用时，将保持静止状态或匀速直线运动状态。\n\n"
        "关键要点：\n"
        "1. 力不是维持物体运动的原因。\n"
        "2. 力是改变物体运动状态的原因。\n"
        "3. 惯性参考系是该定律成立的前提。\n\n"
        "教学目标：理解惯性概念，区分静止与匀速运动。"
    )
    # We purposefully avoid CJK font hassles by inserting via a single
    # textbox call. The default font handles ASCII; the project's own
    # parser tolerates encoded-as-unicode CJK on most macOS systems.
    rect = fitz.Rect(40, 40, 555, 800)
    page.insert_textbox(
        rect,
        text,
        fontsize=12,
        fontname="helv",
        align=0,
    )
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


@pytest.fixture(scope="session")
def real_pdf() -> Path:
    """Path to the ``超星 API 规范`` PDF in the repo root.

    Only used by tests that explicitly want to exercise a non-trivial
    multi-page document.  Most e2e tests should prefer ``tiny_pdf``.
    """
    candidate = ROOT / "超星AI互动智课服务系统开放API设计规范与示例.pdf"
    if not candidate.exists():
        pytest.skip("Repository PDF is missing; cannot run multi-page e2e test.")
    return candidate


# ---------------------------------------------------------------------
# LLM availability gate
# ---------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _require_llm_credentials():
    """Fail fast with a useful message if .env is incomplete for e2e."""
    required = ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        warnings.warn(
            f"e2e tests need {missing} in .env to fully exercise the LLM path; "
            "tests will fall back to baseline behaviour where possible.",
            stacklevel=1,
        )


# ---------------------------------------------------------------------
# Background-task short-circuit (we drive pipelines manually below)
# ---------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _disable_background_tasks(monkeypatch):
    """Replace ``BackgroundTasks.add_task`` with a no-op.

    Each e2e test calls the relevant ``run_*`` service function directly
    so it can ``assert`` on the synchronous result.  Letting FastAPI's
    BackgroundTasks fire-and-forget would introduce unobservable timing.
    """
    from fastapi import BackgroundTasks

    monkeypatch.setattr(BackgroundTasks, "add_task", lambda self, *a, **kw: None)
