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


def _market_status() -> dict:
    """Return current market status and a human-readable warning if closed."""
    from app.scheduler.jobs import is_market_open
    from zoneinfo import ZoneInfo
    from datetime import datetime
    et = ZoneInfo("America/New_York")
    now = datetime.now(et)
    open_ = is_market_open()
    msg = None
    if not open_:
        if now.weekday() >= 5:
            msg = f"Market is closed (weekend). DAY orders will be cancelled immediately — use GTC to queue for Monday open."
        elif now.hour < 9 or (now.hour == 9 and now.minute < 30):
            opens_in = (now.replace(hour=9, minute=30, second=0) - now)
            msg = f"Market opens in {int(opens_in.seconds/60)} minutes. DAY orders placed now will be cancelled — use GTC to queue for open."
        else:
            msg = f"Market is closed (after 4 PM ET). DAY orders will be cancelled immediately — use GTC to queue for tomorrow's open."
    return {"open": open_, "warning": msg, "time_et": now.strftime("%I:%M %p ET")}


async def _place_and_verify(order_spec: Any, label: str) -> dict:
    """Place an order then poll Schwab 4 seconds later to confirm actual status."""
    import asyncio
    from app.schwab.client import schwab_client

    result = await schwab_client.place_order(order_spec)
    order_id = result.get("orderId", "")

    if order_id:
        await asyncio.sleep(4)
        try:
            status_resp = await schwab_client.get_order(order_id)
            actual_status = status_resp.get("status", "UNKNOWN")
            result["status"] = actual_status
            if actual_status in ("CANCELED", "CANCELLED", "REJECTED"):
                cancel_reason = status_resp.get("cancelTime") or status_resp.get("statusDescription", "")
                result["warning"] = (
                    f"⚠️ Order was {actual_status} by Schwab immediately after placement. "
                    f"This usually means the market is closed and the order used DAY duration. "
                    f"Try again with duration=GTC to queue for next market open."
                    + (f" Schwab reason: {cancel_reason}" if cancel_reason else "")
                )
                logger.warning("Order cancelled by Schwab after placement", label=label, order_id=order_id, status=actual_status)
            else:
                logger.info("Order placed and verified", label=label, order_id=order_id, status=actual_status)
        except Exception as exc:
            logger.warning("Could not verify order status after placement", order_id=order_id, error=str(exc))

    return result


async def handle_tool_call(name: str, tool_input: dict[str, Any]) -> Any:
    """Handle a direct-trading tool call. Returns None if name is not owned by this skill."""
    if name not in _TOOL_NAMES:
        return None

    try:
        import schwab as schwab_lib
        import schwab.orders.common as common

        duration_str = tool_input.get("duration", "DAY")
        duration = _schwab_duration(duration_str)
        mkt = _market_status()

        # Block MARKET orders when market is closed — they'll always cancel
        if not mkt["open"] and tool_input.get("order_type", "LIMIT") == "MARKET":
            return {
                "error": f"Cannot place MARKET orders when market is closed ({mkt['time_et']}). "
                         f"Use a LIMIT order with duration=GTC to queue for next market open."
            }

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
            result = await _place_and_verify(order, f"buy_shares {tool_input['symbol']}")
            out = {"action": "buy_shares", **tool_input, "result": result}
            if mkt["warning"]: out["market_warning"] = mkt["warning"]
            return out

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
            result = await _place_and_verify(order, f"sell_shares {tool_input['symbol']}")
            out = {"action": "sell_shares", **tool_input, "result": result}
            if mkt["warning"]: out["market_warning"] = mkt["warning"]
            return out

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

            result = await _place_and_verify(order, f"buy_option {raw_symbol}")
            out = {"action": "buy_option", "symbol": raw_symbol, "contracts": contracts,
                   "order_type": order_type, "limit_price": limit_price,
                   "duration": duration_str, "result": result}
            if mkt["warning"]: out["market_warning"] = mkt["warning"]
            return out

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

            result = await _place_and_verify(order, f"sell_option_manual {raw_symbol}")
            out = {"action": "sell_option_manual", "symbol": raw_symbol, "contracts": contracts,
                   "order_type": order_type, "limit_price": limit_price,
                   "duration": duration_str, "result": result}
            if mkt["warning"]: out["market_warning"] = mkt["warning"]
            return out

    except Exception as exc:
        logger.error("Direct trading tool handler error", tool=name, error=str(exc))
        return {"error": str(exc)}

    return None
