"""Shim for backward compatibility — redirects to src.claude_agents.narration_from_ppt.

旧入口已迁移至 src.claude_agents.narration_from_ppt。请改用：

    python -m src.claude_agents.narration_from_ppt -s "..." -a "..."
"""

import warnings
import sys

warnings.warn(
    "narration_generation.py is deprecated. Use `python -m src.claude_agents.narration_from_ppt` instead.",
    DeprecationWarning,
    stacklevel=2,
)

from src.claude_agents.narration_from_ppt import main

if __name__ == "__main__":
    main()
