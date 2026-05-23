"""
Skill registry — aggregates all agent skills into a single tool list and dispatcher.

Usage in agent.py:
    from app.agent.skills import ALL_TOOLS, handle_tool_call
"""
from typing import Any

import structlog

from app.agent.skills.wheel_strategy import (
    TOOL_DEFINITIONS as WHEEL_TOOLS,
    handle_tool_call as wheel_handler,
)
from app.agent.skills.market_data import (
    TOOL_DEFINITIONS as MARKET_TOOLS,
    handle_tool_call as market_handler,
)
from app.agent.skills.direct_trading import (
    TOOL_DEFINITIONS as TRADING_TOOLS,
    handle_tool_call as trading_handler,
)
from app.agent.skills.research import (
    TOOL_DEFINITIONS as RESEARCH_TOOLS,
    handle_tool_call as research_handler,
)
from app.agent.skills.social_intel import (
    TOOL_DEFINITIONS as SOCIAL_TOOLS,
    handle_tool_call as social_handler,
)

logger = structlog.get_logger(__name__)

ALL_TOOLS = WHEEL_TOOLS + MARKET_TOOLS + TRADING_TOOLS + RESEARCH_TOOLS + SOCIAL_TOOLS

_SKILL_HANDLERS = [
    wheel_handler,
    market_handler,
    trading_handler,
    research_handler,
    social_handler,
]


async def handle_tool_call(name: str, input: dict[str, Any]) -> Any:
    """
    Dispatch a tool call to the owning skill handler.

    Each skill handler returns None if the tool name is not its own,
    so we try each in order and return the first non-None result.
    """
    for handler in _SKILL_HANDLERS:
        result = await handler(name, input)
        if result is not None:
            return result
    logger.warning("No skill handler claimed tool", tool=name)
    return {"error": f"Unknown tool: {name}"}


__all__ = ["ALL_TOOLS", "handle_tool_call"]
