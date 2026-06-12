"""Public entry points for src.agents.

Imports are lazy (PEP 562) so importing this package never eagerly pulls
in heavy optional dependencies (e.g. the student agent's database stack).
Each symbol is resolved on first attribute access.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # for type checkers only — no runtime cost
    from .courseware_flash_narration import run_courseware_flash_narration
    from .courseware_flash_render import run_courseware_flash_render
    from .courseware_flash_slideplan import run_courseware_flash_slideplan
    from .courseware_pro_render import run_courseware_pro_render
    from .student import build_student_agent_turn, run_student_agent


__all__ = [
    "build_student_agent_turn",
    "run_courseware_flash_narration",
    "run_courseware_flash_render",
    "run_courseware_flash_slideplan",
    "run_courseware_pro_render",
    "run_student_agent",
]


_LAZY_EXPORTS = {
    "run_courseware_flash_narration": ".courseware_flash_narration",
    "run_courseware_flash_render": ".courseware_flash_render",
    "run_courseware_flash_slideplan": ".courseware_flash_slideplan",
    "run_courseware_pro_render": ".courseware_pro_render",
    "build_student_agent_turn": ".student",
    "run_student_agent": ".student",
}


def __getattr__(name: str):
    """Resolve top-level exports on first access."""
    target = _LAZY_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module 'src.agents' has no attribute {name!r}")
    module = import_module(target, package=__name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
