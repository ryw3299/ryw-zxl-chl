"""OpenHands tool adapters for student agent tools.

This package provides OpenHands SDK tool wrappers around the existing business tools:
- SearchTool -> SearchOpenHandsTool
- RetrieveTool -> RetrieveOpenHandsTool
- SessionTool -> SessionOpenHandsTool
- MemoryTool -> MemoryOpenHandsTool

Each adapter follows the OpenHands SDK patterns:
- Action (input schema)
- Observation (output schema)
- ToolDefinition (tool declaration)
- ToolExecutor (execution logic)
"""

from src.tools.openhands.game_tool import GameOpenHandsTool
from src.tools.openhands.memory_tool import MemoryOpenHandsTool
from src.tools.openhands.retrieve_tool import RetrieveOpenHandsTool
from src.tools.openhands.search_tool import SearchOpenHandsTool
from src.tools.openhands.session_tool import SessionOpenHandsTool

__all__ = [
    "GameOpenHandsTool",
    "SearchOpenHandsTool",
    "RetrieveOpenHandsTool",
    "SessionOpenHandsTool",
    "MemoryOpenHandsTool",
]
