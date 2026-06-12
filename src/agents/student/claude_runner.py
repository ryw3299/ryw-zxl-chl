"""Shim for backward compatibility.

This module re-exports ``build_student_agent_turn`` and ``run_student_agent``
from ``src.claude_agents.student_qa``. New code should import directly from
``src.claude_agents.student_qa`` instead.
"""

from src.claude_agents.student_qa import build_student_agent_turn, run_student_agent

__all__ = [
    "build_student_agent_turn",
    "run_student_agent",
]
