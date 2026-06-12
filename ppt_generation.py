"""Shim for backward compatibility — redirects to src.claude_agents.courseware_flash.

旧入口已迁移至 src.claude_agents.courseware_flash。请改用：

    python -m src.claude_agents.courseware_flash -i "..." -a "..."
"""

import warnings
import sys

warnings.warn(
    "ppt_generation.py is deprecated. Use `python -m src.claude_agents.courseware_flash` instead.",
    DeprecationWarning,
    stacklevel=2,
)

from src.claude_agents.courseware_flash import main

if __name__ == "__main__":
    main()
