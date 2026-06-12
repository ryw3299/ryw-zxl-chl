"""Shared runtime helpers for the four ``courseware_*`` entry modules.

The L3 entry functions (``run_courseware_flash_slideplan``,
``run_courseware_flash_render``, ``run_courseware_flash_narration``,
``run_courseware_pro_render``) used to duplicate the same ``load_dotenv``
+ logger setup + path-constant block at the top of each file.

This module centralises:

* canonical project / ppt-master / claude_sdk paths
* the ``.env`` loading idiom (with optional explicit override)
* the structured-logger factory call

so each entry function only has to handle its own pipeline-specific logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
PPT_MASTER_DIR: Path = PROJECT_ROOT / "ppt-master"
COURSEWARE_FLASH_DIR: Path = PPT_MASTER_DIR / "skills" / "courseware-flash"
COURSEWARE_FLASH_SCRIPTS_DIR: Path = COURSEWARE_FLASH_DIR / "scripts"
PPT_MASTER_SCRIPTS_DIR: Path = PPT_MASTER_DIR / "skills" / "ppt-master" / "scripts"
AUTO_CONVERT_SCRIPT: Path = COURSEWARE_FLASH_SCRIPTS_DIR / "auto_source_convert.py"
SLIDE_PLAN_SCHEMA_PATH: Path = COURSEWARE_FLASH_DIR / "templates" / "slide_plan_schema.json"
CLAUDE_SDK_ROOT: Path = PROJECT_ROOT / "claude_sdk"

DETAIL_LEVELS: tuple[str, ...] = ("A", "B", "C", "D")


def load_courseware_env(env_path: Optional[str] = None) -> None:
    """Load the project ``.env`` (or an explicit override) with ``override=True``.

    ``override=True`` matches the legacy behaviour of every courseware entry
    function and prevents stale env values from the host shell (e.g. a Claude
    Code wrapper) from leaking into provider configuration.
    """
    if env_path:
        load_dotenv(dotenv_path=env_path, override=True)
        return
    default_env = PROJECT_ROOT / ".env"
    if default_env.exists():
        load_dotenv(dotenv_path=default_env, override=True)


def get_courseware_logger(name: str, log_file: Optional[str] = None):
    """Return a structured logger using :func:`src.utils.logging_utils.get_logger`."""
    from src.utils.logging_utils import get_logger  # local import to avoid cycles

    return get_logger(name, log_file=log_file)


__all__ = [
    "PROJECT_ROOT",
    "PPT_MASTER_DIR",
    "COURSEWARE_FLASH_DIR",
    "COURSEWARE_FLASH_SCRIPTS_DIR",
    "PPT_MASTER_SCRIPTS_DIR",
    "AUTO_CONVERT_SCRIPT",
    "SLIDE_PLAN_SCHEMA_PATH",
    "CLAUDE_SDK_ROOT",
    "DETAIL_LEVELS",
    "load_courseware_env",
    "get_courseware_logger",
]
