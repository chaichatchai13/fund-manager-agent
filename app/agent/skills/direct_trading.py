"""
Direct trading skill — buy/sell shares and options outside the automated rules system.
Always confirm with the user before calling any order-placement tool.
"""
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "buy_shares",
        "description": "Buy shares of a stock at market or limit price. Always confirm with user before calling.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "quantity": {"type": "integer"},
                "order_type": {"type": "string", "enum": ["MARKET", "LIMIT"], "default": "LIMIT"},
                "limit_price": {"type": "number", "description": "Required if order_type=LIMIT"},
            },
            "required": ["symbol", "quantity"],
        },
    },
    {
        "name": "sell_shares",
        "description": "Sell shares of a stock at market or limit price. Always confirm with user before calling.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "quantity": {"type": "integer"},
                "order_type": {"type": "string", "enum": ["MARKET", "LIMIT"], "default": "LIMIT"},
                "limit_price": {"type": "number"},
            },
            "required": ["symbol", "quantity"],
        },
    },
    {
        "name": "buy_option",
        "description": "Buy to open a call or put option. Always confirm details with user before calling.",
        "input_schema": {
            "type": "object",
            "properties": {
                "option_symbol": {"type": "string", "description": "OCC-format symbol e.g. TSLA_260620C00300000"},
                "contracts": {"type": "integer"},
                "order_type": {"type": "string", "enum": ["MARKET", "LIMIT"], "default": "LIMIT"},
                "limit_price": {"type": "number"},
            },
            "required": ["option_symbol", "contracts"],
        },
    },
    {
        "name": "sell_option_manual",
        "description": "Manually sell to open a put or call option outside of the automated rules system.",
        "input_schema": {
            "type": "object",
            "properties": {
                "option_symbol": {"type": "string"},
                "contracts": {"type": "integer"},
                "order_type": {"type": "string", "enum": ["MARKET", "LIMIT"], "default": "LIMIT"},
                "limit_price": {"type": "number"},
            },
            "required": ["option_symbol", "contracts"],
        },
    },
]

_TOOL_NAMES = {t["name"] for t in TOOL_DEFINITIONS}


async def handle_tool_call(name: str, tool_input: dict[str, Any]) -> Any:
    """Handle a direct-trading tool call. Returns None if name is not owned by this skill."""
    if name not in _TOOL_NAMES:
        return None

    try:
        import schwab as schwab_lib
        from app.schwab.client import schwab_client

        if name == "buy_shares":
            if tool_input.get("order_type", "LIMIT") == "LIMIT":
                order = schwab_lib.orders.equities.equity_buy_limit(
                    tool_input["symbol"], tool_input["quantity"], tool_input.get("limit_price", 0)
                )
            else:
                order = schwab_lib.orders.equities.equity_buy_market(
                    tool_input["symbol"], tool_input["quantity"]
                )
            result = await schwab_client.place_order(order)
            return {"action": "buy_shares", **tool_input, "result": result}

        if name == "sell_shares":
            if tool_input.get("order_type", "LIMIT") == "LIMIT":
                order = schwab_lib.orders.equities.equity_sell_limit(
                    tool_input["symbol"], tool_input["quantity"], tool_input.get("limit_price", 0)
                )
            else:
                order = schwab_lib.orders.equities.equity_sell_market(
                    tool_input["symbol"], tool_input["quantity"]
                )
            result = await schwab_client.place_order(order)
            return {"action": "sell_shares", **tool_input, "result": result}

        if name in ("buy_option", "sell_option_manual"):
            # Full implementation planned for next sprint
            return {"error": "Direct option trading not yet implemented — use rules for automated selling"}

    except Exception as exc:
        logger.error("Direct trading tool handler error", tool=name, error=str(exc))
        return {"error": str(exc)}

    return None
