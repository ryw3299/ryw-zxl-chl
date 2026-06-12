"""Centralised runtime path management for ChaoXingAgent.

All runtime artifacts (uploads, audio outputs, rendered PPTs, RAG indices,
session/history databases, logs, courseware workspace) used to live in
many ad-hoc locations under ``data/`` or hard-coded constants.  This
module gathers them in **one** place so the rest of the codebase never
constructs runtime paths by hand.

Usage
-----
.. code-block:: python

    from src.utils.paths import paths

    paths.ensure()                       # create every runtime dir
    audio_dir = paths.audio_dir          # Path
    session_db_path = paths.session_db   # Path

Every property returns a :class:`pathlib.Path` already resolved against
``project_root``.  ``ensure()`` is idempotent and safe to call at
service startup.

Override behaviour
------------------
- Values are sourced from :mod:`src.api.config` ``settings`` (which in
  turn read ``.env`` via ``pydantic-settings``).
- Any unset path falls back to a deterministic location under
  ``<project_root>/data/runtime/...``.  This keeps a clean separation
  between repo-tracked sample data in ``data/`` and runtime artifacts in
  ``data/runtime/``.
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_RUNTIME_ROOT = _PROJECT_ROOT / "data" / "runtime"


def _resolve(value: str | os.PathLike[str] | None, default: Path) -> Path:
    """Return an absolute :class:`Path`, falling back to ``default``."""
    if value is None or str(value).strip() == "":
        return default
    candidate = Path(str(value)).expanduser()
    if not candidate.is_absolute():
        candidate = (_PROJECT_ROOT / candidate).resolve()
    return candidate


@dataclass(frozen=True)
class RuntimePaths:
    """All runtime directories and file locations for ChaoXingAgent."""

    project_root: Path

    # ── lazy: read from src.api.config.settings at access time ──────
    @cached_property
    def _settings(self):  # noqa: D401 - simple lazy accessor
        # Imported lazily to avoid a circular import (config imports nothing
        # from utils, but utils may be imported by config consumers).
        from src.api.config import settings

        return settings

    # ── top-level runtime root ──────────────────────────────────────
    @cached_property
    def runtime_root(self) -> Path:
        return _resolve(
            getattr(self._settings, "RUNTIME_DIR", None),
            _DEFAULT_RUNTIME_ROOT,
        )

    # ── per-purpose directories ─────────────────────────────────────
    @cached_property
    def uploads_dir(self) -> Path:
        return _resolve(self._settings.UPLOAD_DIR, self.runtime_root / "uploads")

    @cached_property
    def audio_dir(self) -> Path:
        return _resolve(self._settings.AUDIO_DIR, self.runtime_root / "audio")

    @cached_property
    def render_dir(self) -> Path:
        return _resolve(self._settings.RENDER_DIR, self.runtime_root / "renders")

    @cached_property
    def rag_index_dir(self) -> Path:
        return _resolve(
            getattr(self._settings, "RAG_INDEX_DIR", None),
            self.project_root / "data" / "rag_indices",
        )

    @cached_property
    def log_dir(self) -> Path:
        return _resolve(
            getattr(self._settings, "LOG_DIR", None),
            self.runtime_root / "logs",
        )

    @cached_property
    def workspace_dir(self) -> Path:
        """Root for Claude SDK / courseware project artifacts."""
        return _resolve(
            getattr(self._settings, "WORKSPACE_DIR", None),
            self.project_root / "ChaoXingAgentWorkspace",
        )

    @cached_property
    def projects_dir(self) -> Path:
        """``<workspace>/projects`` — one subdir per courseware project."""
        return self.workspace_dir / "projects"

    @cached_property
    def student_runs_dir(self) -> Path:
        """``<runtime>/student_qa_runs`` — per-session Claude workspace."""
        return self.runtime_root / "student_qa_runs"

    # ── file locations ──────────────────────────────────────────────
    @cached_property
    def session_db(self) -> Path:
        return _resolve(
            getattr(self._settings, "SESSION_DB_PATH", None),
            self.runtime_root / "memory" / "student_sessions.db",
        )

    @cached_property
    def history_db(self) -> Path:
        return _resolve(
            getattr(self._settings, "HISTORY_DB_PATH", None),
            self.runtime_root / "memory" / "student_qa_history.db",
        )

    # ── lifecycle ───────────────────────────────────────────────────
    def ensure(self, extras: Iterable[Path] | None = None) -> None:
        """Create every managed directory if it does not exist yet."""
        for d in (
            self.runtime_root,
            self.uploads_dir,
            self.audio_dir,
            self.render_dir,
            self.rag_index_dir,
            self.log_dir,
            self.workspace_dir,
            self.projects_dir,
            self.student_runs_dir,
            self.session_db.parent,
            self.history_db.parent,
            *(extras or ()),
        ):
            d.mkdir(parents=True, exist_ok=True)

    def as_dict(self) -> dict[str, str]:
        """Snapshot useful for /health endpoints and debugging."""
        return {
            "project_root": str(self.project_root),
            "runtime_root": str(self.runtime_root),
            "uploads_dir": str(self.uploads_dir),
            "audio_dir": str(self.audio_dir),
            "render_dir": str(self.render_dir),
            "rag_index_dir": str(self.rag_index_dir),
            "log_dir": str(self.log_dir),
            "workspace_dir": str(self.workspace_dir),
            "projects_dir": str(self.projects_dir),
            "student_runs_dir": str(self.student_runs_dir),
            "session_db": str(self.session_db),
            "history_db": str(self.history_db),
        }


paths = RuntimePaths(project_root=_PROJECT_ROOT)
"""Singleton :class:`RuntimePaths` shared by the whole codebase."""


__all__ = ["paths", "RuntimePaths"]
