# Backwards compatibility shim — all tool definitions and handlers have moved to app/agent/skills/
from app.agent.skills import ALL_TOOLS as TOOL_DEFINITIONS, handle_tool_call  # noqa: F401

__all__ = ["TOOL_DEFINITIONS", "handle_tool_call"]
