"""Student-side agent entry points (backend-pluggable).

The active backend is selected by the ``STUDENT_AGENT_BACKEND`` environment
variable:

* ``"claude"`` (default) — :mod:`src.claude_agents.student_qa`
* ``"openhands"`` — :mod:`src.agents.student.agent`

If the configured backend cannot be imported (e.g. its SDK is not installed
in the current environment), the import quietly falls back to the OpenHands
backend.  This avoids breaking unrelated callers — including unit tests
that only need :mod:`response_builder` — when an optional dependency is
missing.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def _select_backend():
    backend = os.getenv("STUDENT_AGENT_BACKEND", "claude").lower()
    if backend == "claude":
        try:
            from src.claude_agents.student_qa import (  # noqa: WPS433
                build_student_agent_turn,
                run_student_agent,
            )

            return build_student_agent_turn, run_student_agent
        except ImportError as exc:
            logger.warning(
                "Claude backend unavailable (%s); falling back to OpenHands.",
                exc,
            )
    # OpenHands fallback (also the explicit "openhands" path).
    from .agent import build_student_agent_turn, run_student_agent  # noqa: WPS433

    return build_student_agent_turn, run_student_agent


build_student_agent_turn, run_student_agent = _select_backend()


__all__ = [
    "build_student_agent_turn",
    "run_student_agent",
]
