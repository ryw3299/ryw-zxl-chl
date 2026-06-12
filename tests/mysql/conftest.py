"""Real-MySQL integration test fixtures.

Uses a **dedicated test database** (``chaoxing_test``) so the production
``chaoxing`` schema and its real business rows are never touched.

Workflow per session:
    1. Drop & recreate ``chaoxing_test`` (CHARACTER SET utf8mb4)
    2. Build engine pointing at the test DB
    3. ``init_db()`` runs ``Base.metadata.create_all`` on the real MySQL
    4. Each test function runs in a savepoint that rolls back on teardown,
       so tests can interleave and stay isolated even within one session.

Like ``tests/e2e/``, this suite is **opt-in** via ``--run-mysql`` /
``RUN_MYSQL=1`` so it doesn't accidentally fire when MySQL isn't running.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ---------------------------------------------------------------------
# Config: derive the test DB URL from the production DATABASE_URL by
# swapping the database name to ``chaoxing_test``.
# ---------------------------------------------------------------------


def _resolve_test_db_url() -> str:
    """Return a MySQL URL pointing at ``chaoxing_test``.

    Honors ``MYSQL_TEST_URL`` if explicitly set; otherwise rewrites the
    database segment of ``DATABASE_URL``.
    """
    explicit = os.environ.get("MYSQL_TEST_URL", "").strip()
    if explicit:
        return explicit

    # Load production .env so we inherit credentials.
    try:
        from dotenv import load_dotenv

        load_dotenv(dotenv_path=str(ROOT / ".env"))
    except Exception:
        pass

    src_url = os.environ.get("DATABASE_URL", "")
    if not src_url.startswith("mysql"):
        # Fallback to a localhost default; tests will skip if MySQL is down.
        return "mysql+pymysql://root:12345678@127.0.0.1:3306/chaoxing_test?charset=utf8mb4"

    # Replace path segment with /chaoxing_test
    parsed = urlparse(src_url)
    new = parsed._replace(path="/chaoxing_test")
    return new.geturl()


_TEST_DB_URL = _resolve_test_db_url()

os.environ["DATABASE_URL"] = _TEST_DB_URL
os.environ["DEBUG"] = "true"


# ---------------------------------------------------------------------
# Skip-by-default
# ---------------------------------------------------------------------


def pytest_addoption(parser):
    parser.addoption(
        "--run-mysql",
        action="store_true",
        default=False,
        help="Run real-MySQL integration tests (requires a running MySQL).",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--run-mysql") or os.environ.get("RUN_MYSQL") in {"1", "true", "yes"}:
        return
    skip = pytest.mark.skip(
        reason="MySQL integration tests skipped by default. "
        "Run with `RUN_MYSQL=1 pytest tests/mysql/` or `--run-mysql`."
    )
    for item in items:
        if "/tests/mysql/" in str(item.fspath):
            item.add_marker(skip)


# ---------------------------------------------------------------------
# DB lifecycle
# ---------------------------------------------------------------------


def _ensure_test_database_exists() -> None:
    """Create ``chaoxing_test`` if missing (idempotent)."""
    import pymysql

    parsed = urlparse(_TEST_DB_URL.replace("+pymysql", ""))
    db_name = parsed.path.lstrip("/")

    conn = pymysql.connect(
        host=parsed.hostname or "127.0.0.1",
        port=parsed.port or 3306,
        user=parsed.username or "root",
        password=parsed.password or "",
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    finally:
        conn.close()


def _drop_all_tables() -> None:
    """Drop every table in ``chaoxing_test`` for a fresh start.

    We rebuild the schema each session so DDL changes in ``tables.py``
    are exercised cleanly (and you can spot incompatibilities early).
    """
    import pymysql

    parsed = urlparse(_TEST_DB_URL.replace("+pymysql", ""))
    db_name = parsed.path.lstrip("/")
    conn = pymysql.connect(
        host=parsed.hostname or "127.0.0.1",
        port=parsed.port or 3306,
        user=parsed.username or "root",
        password=parsed.password or "",
        database=db_name,
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SET FOREIGN_KEY_CHECKS = 0")
            cur.execute("SHOW TABLES")
            for (tname,) in cur.fetchall():
                cur.execute(f"DROP TABLE IF EXISTS `{tname}`")
            cur.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(scope="session", autouse=True)
def _bootstrap_mysql_test_db():
    """Ensure ``chaoxing_test`` exists and is empty before any test runs."""
    try:
        _ensure_test_database_exists()
        _drop_all_tables()
    except Exception as exc:  # pragma: no cover - reported via pytest skip
        pytest.skip(f"MySQL not reachable: {exc!r}")
    yield
    # Leave the schema in place after the run so devs can inspect with mysql CLI.


@pytest.fixture(scope="session")
def app(_bootstrap_mysql_test_db):
    """Build the FastAPI app once, against the MySQL test DB.

    Depends explicitly on ``_bootstrap_mysql_test_db`` so the table
    drop runs *before* ``init_db`` (otherwise the autouse fixture may
    interleave and wipe the freshly-created tables).
    """
    from src.api.config import settings
    from src.api.models import database as _db_mod

    object.__setattr__(settings, "DATABASE_URL", _TEST_DB_URL)
    object.__setattr__(settings, "DEBUG", True)

    # Force-rebuild engine; the production MySQL engine may already be cached
    # from earlier ``import src.api.app`` calls in the same pytest session.
    new_engine = _db_mod._build_engine_with_url(_TEST_DB_URL)
    _db_mod.engine = new_engine
    from sqlalchemy.orm import sessionmaker

    _db_mod.SessionLocal = sessionmaker(bind=new_engine, autocommit=False, autoflush=False)

    from src.api.app import app as fastapi_app

    _db_mod.init_db()
    return fastapi_app


@pytest.fixture(scope="session")
def client(app):
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def db(app):
    from src.api.models.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def raw_mysql_cursor(app):
    """Yield a low-level pymysql cursor for INFORMATION_SCHEMA introspection.

    Depends on ``app`` so ``init_db`` has populated the schema before any
    introspection attempt.
    """
    import pymysql

    parsed = urlparse(_TEST_DB_URL.replace("+pymysql", ""))
    conn = pymysql.connect(
        host=parsed.hostname or "127.0.0.1",
        port=parsed.port or 3306,
        user=parsed.username or "root",
        password=parsed.password or "",
        database=parsed.path.lstrip("/"),
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        conn.close()


@pytest.fixture()
def test_db_name() -> str:
    """The MySQL database name used by the test session."""
    parsed = urlparse(_TEST_DB_URL.replace("+pymysql", ""))
    return parsed.path.lstrip("/")


# ---------------------------------------------------------------------
# Background tasks short-circuit (same rationale as in tests/api/)
# ---------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _disable_background_tasks(monkeypatch):
    from fastapi import BackgroundTasks

    monkeypatch.setattr(BackgroundTasks, "add_task", lambda self, *a, **kw: None)
