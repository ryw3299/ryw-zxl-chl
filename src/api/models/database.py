from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text  # noqa: F401 - text kept for downstream imports
from sqlalchemy.exc import NoSuchModuleError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.api.config import settings
from src.utils.paths import paths


class Base(DeclarativeBase):
    pass


def _build_engine_with_url(database_url: str):
    if database_url.startswith("sqlite"):
        return create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            echo=settings.DEBUG,
        )
    return create_engine(
        database_url,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_recycle=settings.DB_POOL_RECYCLE,
        pool_pre_ping=True,
        echo=settings.DEBUG,
    )


def _build_engine():
    """Build the SQLAlchemy engine, falling back to SQLite if MySQL is unreachable.

    The fallback keeps local dev usable when the configured MySQL is not
    running or its driver (``pymysql``) is not installed.  In that case we
    relocate to a deterministic SQLite file under ``paths.runtime_root``
    and patch :data:`settings.DATABASE_URL` so other modules see the
    effective URL.
    """
    url = settings.DATABASE_URL
    try:
        engine = _build_engine_with_url(url)
        engine.connect().close()  # eagerly trigger driver import & connection
        return engine
    except (ModuleNotFoundError, NoSuchModuleError, Exception) as exc:  # noqa: BLE001
        import logging

        fallback_path = paths.runtime_root / "chaoxing_dev.db"
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        fallback_url = f"sqlite:///{fallback_path}"
        logging.getLogger(__name__).warning(
            "Primary DATABASE_URL=%s unavailable (%s); falling back to %s",
            url,
            type(exc).__name__,
            fallback_url,
        )
        # Patch settings so the rest of the codebase sees the effective URL.
        try:
            object.__setattr__(settings, "DATABASE_URL", fallback_url)
        except (AttributeError, TypeError):
            # Pydantic models may forbid mutation in some versions; harmless.
            pass
        return _build_engine_with_url(fallback_url)


engine = _build_engine()

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    # Importing tables here ensures models are registered before create_all.
    from src.api.models import tables  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_compatible_schema()


def _ensure_compatible_schema() -> None:
    """Add lightweight local-dev columns that create_all cannot backfill."""
    inspector = inspect(engine)
    dialect = engine.dialect.name
    table_names = set(inspector.get_table_names())
    statements: list[str] = []

    if "users" in table_names:
        user_columns = {column["name"] for column in inspector.get_columns("users")}
        if "password_hash" not in user_columns:
            if dialect == "mysql":
                statements.append(
                    "ALTER TABLE users ADD COLUMN password_hash TEXT NULL COMMENT 'Password hash for local accounts'"
                )
            else:
                statements.append("ALTER TABLE users ADD COLUMN password_hash TEXT")

    if "lessons" in table_names:
        lesson_columns = {column["name"] for column in inspector.get_columns("lessons")}
        lesson_column_specs = {
            "courseware_project_dir": ("VARCHAR(1024) NULL COMMENT '课件项目目录'", "VARCHAR(1024)"),
            "slide_plan_path": ("VARCHAR(1024) NULL COMMENT 'slide_plan.json路径'", "VARCHAR(1024)"),
            "slide_plan_json": ("LONGTEXT NULL COMMENT 'slide_plan.json内容'", "TEXT"),
            "courseware_status": ("VARCHAR(32) NULL COMMENT '课件链路状态'", "VARCHAR(32)"),
            "courseware_render_mode": ("VARCHAR(16) NULL COMMENT '课件渲染模式'", "VARCHAR(16)"),
            "narration_paths": ("LONGTEXT NULL COMMENT '四档讲稿路径JSON'", "TEXT"),
            "courseware_error": ("TEXT NULL COMMENT '课件链路错误信息'", "TEXT"),
        }
        for column_name, (mysql_spec, sqlite_spec) in lesson_column_specs.items():
            if column_name not in lesson_columns:
                spec = mysql_spec if dialect == "mysql" else sqlite_spec
                statements.append(f"ALTER TABLE lessons ADD COLUMN {column_name} {spec}")

    if statements:
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(text(statement))
