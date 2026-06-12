# claude_sdk/tools/registry.py

from typing import Any
from claude_agent_sdk import create_sdk_mcp_server

# Student QA agent does not need custom MCP tools by default.
# The registry is kept minimal; add entries here if you need
# domain-specific tools (e.g. game generation).
TOOL_REGISTRY: dict[str, Any] = {}


def build_mcp_servers(custom_tools: list[str] | None) -> tuple[dict[str, Any], list[str]]:
    custom_tools = custom_tools or []

    if not custom_tools:
        return {}, []

    unknown = [name for name in custom_tools if name not in TOOL_REGISTRY]
    if unknown:
        raise ValueError(f"Unknown custom tools: {unknown}")

    selected_tools = [TOOL_REGISTRY[name] for name in custom_tools]

    server_name = "chaoxingagent"

    server = create_sdk_mcp_server(
        name=server_name,
        version="0.1.0",
        tools=selected_tools,
    )

    exposed_names = [
        f"mcp__{server_name}__{tool_name}"
        for tool_name in custom_tools
    ]

    return {server_name: server}, exposed_names
