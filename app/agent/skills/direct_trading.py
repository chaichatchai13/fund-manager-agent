"""
Direct trading skill — buy/sell shares and options outside the automated rules system.
Always confirm with the user before calling any order-placement tool.

Supported durations:
  DAY  — expires at market close if unfilled
  GTC  — Good Till Cancelled (stays open until filled or manually cancelled)

Note: MARKET orders only support DAY duration (GTC market orders are not supported by Schwab).
"""
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_DURATION_DESC = "Order duration: DAY (expires at market close) or GTC (Good Till Cancelled). Defaults to DAY. GTC only valid with LIMIT orders."

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
                "duration": {"type": "string", "enum": ["DAY", "GTC"], "default": "DAY", "description": _DURATION_DESC},
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
                "limit_price": {"type": "number", "description": "Required if order_type=LIMIT"},
                "duration": {"type": "string", "enum": ["DAY", "GTC"], "default": "DAY", "description": _DURATION_DESC},
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
                "limit_price": {"type": "number", "description": "Required if order_type=LIMIT"},
                "duration": {"type": "string", "enum": ["DAY", "GTC"], "default": "DAY", "description": _DURATION_DESC},
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
                "option_symbol": {"type": "string", "description": "OCC-format symbol e.g. TSLA_260620P00400000"},
                "contracts": {"type": "integer"},
                "order_type": {"type": "string", "enum": ["MARKET", "LIMIT"], "default": "LIMIT"},
                "limit_price": {"type": "number", "description": "Required if order_type=LIMIT"},
                "duration": {"type": "string", "enum": ["DAY", "GTC"], "default": "DAY", "description": _DURATION_DESC},
            },
            "required": ["option_symbol", "contracts"],
        },
    },
]

_TOOL_NAMES = {t["name"] for t in TOOL_DEFINITIONS}


def _schwab_duration(duration: str):
    """Convert 'DAY' / 'GTC' string to schwab-py Duration enum."""
    import schwab.orders.common as common
    return common.Duration.GOOD_TILL_CANCEL if duration.upper() == "GTC" else common.Duration.DAY


async def handle_tool_call(name: str, tool_input: dict[str, Any]) -> Any:
    """Handle a direct-trading tool call. Returns None if name is not owned by this skill."""
    if name not in _TOOL_NAMES:
        return None

    try:
        import schwab as schwab_lib
        import schwab.orders.common as common
        from app.schwab.client import schwab_client

        duration_str = tool_input.get("duration", "DAY")
        duration = _schwab_duration(duration_str)

        if name == "buy_shares":
            order_type = tool_input.get("order_type", "LIMIT")
            if order_type == "MARKET" and duration_str.upper() == "GTC":
                return {"error": "GTC duration is not supported for MARKET orders. Use LIMIT+GTC or MARKET+DAY."}
            if order_type == "LIMIT":
                if not tool_input.get("limit_price"):
                    return {"error": "limit_price is required for LIMIT orders"}
                order = (
                    schwab_lib.orders.equities.equity_buy_limit(
                        tool_input["symbol"], tool_input["quantity"], tool_input["limit_price"]
                    )
                    .set_duration(duration)
                    .set_session(common.Session.NORMAL)
                    .build()
                )
            else:
                order = (
                    schwab_lib.orders.equities.equity_buy_market(
                        tool_input["symbol"], tool_input["quantity"]
                    )
                    .set_duration(common.Duration.DAY)
                    .set_session(common.Session.NORMAL)
                    .build()
                )
            result = await schwab_client.place_order(order)
            return {"action": "buy_shares", **tool_input, "result": result}

        if name == "sell_shares":
            order_type = tool_input.get("order_type", "LIMIT")
            if order_type == "MARKET" and duration_str.upper() == "GTC":
                return {"error": "GTC duration is not supported for MARKET orders. Use LIMIT+GTC or MARKET+DAY."}
            if order_type == "LIMIT":
                if not tool_input.get("limit_price"):
                    return {"error": "limit_price is required for LIMIT orders"}
                order = (
                    schwab_lib.orders.equities.equity_sell_limit(
                        tool_input["symbol"], tool_input["quantity"], tool_input["limit_price"]
                    )
                    .set_duration(duration)
                    .set_session(common.Session.NORMAL)
                    .build()
                )
            else:
                order = (
                    schwab_lib.orders.equities.equity_sell_market(
                        tool_input["symbol"], tool_input["quantity"]
                    )
                    .set_duration(common.Duration.DAY)
                    .set_session(common.Session.NORMAL)
                    .build()
                )
            result = await schwab_client.place_order(order)
            return {"action": "sell_shares", **tool_input, "result": result}

        if name == "buy_option":
            raw_symbol = tool_input["option_symbol"].replace("_", " ").upper()
            contracts = tool_input["contracts"]
            order_type = tool_input.get("order_type", "LIMIT")
            limit_price = tool_input.get("limit_price")

            if order_type == "MARKET" and duration_str.upper() == "GTC":
                return {"error": "GTC duration is not supported for MARKET orders. Use LIMIT+GTC or MARKET+DAY."}
            if order_type == "LIMIT" and not limit_price:
                return {"error": "limit_price is required for LIMIT orders"}

            import schwab.orders.options as opt

            if order_type == "LIMIT":
                order = (
                    opt.option_buy_to_open_limit(raw_symbol, contracts, limit_price)
                    .set_duration(duration)
                    .set_session(common.Session.NORMAL)
                    .build()
                )
            else:
                order = (
                    opt.option_buy_to_open_market(raw_symbol, contracts)
                    .set_duration(common.Duration.DAY)
                    .set_session(common.Session.NORMAL)
                    .build()
                )

            result = await schwab_client.place_order(order)
            return {"action": "buy_option", "symbol": raw_symbol, "contracts": contracts,
                    "order_type": order_type, "limit_price": limit_price,
                    "duration": duration_str, "result": result}

        if name == "sell_option_manual":
            raw_symbol = tool_input["option_symbol"].replace("_", " ").upper()
            contracts = tool_input["contracts"]
            order_type = tool_input.get("order_type", "LIMIT")
            limit_price = tool_input.get("limit_price")

            if order_type == "MARKET" and duration_str.upper() == "GTC":
                return {"error": "GTC duration is not supported for MARKET orders. Use LIMIT+GTC or MARKET+DAY."}
            if order_type == "LIMIT" and not limit_price:
                return {"error": "limit_price is required for LIMIT orders"}

            import schwab.orders.options as opt

            if order_type == "LIMIT":
                order = (
                    opt.option_sell_to_open_limit(raw_symbol, contracts, limit_price)
                    .set_duration(duration)
                    .set_session(common.Session.NORMAL)
                    .build()
                )
            else:
                order = (
                    opt.option_sell_to_open_market(raw_symbol, contracts)
                    .set_duration(common.Duration.DAY)
                    .set_session(common.Session.NORMAL)
                    .build()
                )

            result = await schwab_client.place_order(order)
            return {"action": "sell_option_manual", "symbol": raw_symbol, "contracts": contracts,
                    "order_type": order_type, "limit_price": limit_price,
                    "duration": duration_str, "result": result}

    except Exception as exc:
        logger.error("Direct trading tool handler error", tool=name, error=str(exc))
        return {"error": str(exc)}

    return None
