"""
Market data skill — live quotes, IV rank, and option chain retrieval via Schwab API.
"""
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

TOOL_DEFINITIONS = [
    {
        "name": "get_quote",
        "description": "Get a live real-time quote for a stock symbol. Returns last price, bid, ask, day change.",
        "input_schema": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]},
    },
    {
        "name": "get_option_chain",
        "description": "Fetch the live option chain for a symbol. Returns strikes, premiums, IV, delta, DTE.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "contract_type": {"type": "string", "enum": ["PUT", "CALL"], "default": "PUT"},
                "min_dte": {"type": "integer", "default": 20},
                "max_dte": {"type": "integer", "default": 60},
            },
            "required": ["symbol"],
        },
    },
    {
        "name": "get_iv_rank",
        "description": "Get the current IV rank (0-100) for a symbol. Higher = more expensive options = better premium selling opportunity.",
        "input_schema": {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]},
    },
]

_TOOL_NAMES = {t["name"] for t in TOOL_DEFINITIONS}


async def handle_tool_call(name: str, tool_input: dict[str, Any]) -> Any:
    """Handle a market-data tool call. Returns None if name is not owned by this skill."""
    if name not in _TOOL_NAMES:
        return None

    try:
        from app.schwab.client import schwab_client

        if name == "get_quote":
            quotes = await schwab_client.get_quotes([tool_input["symbol"]])
            q = quotes.get(tool_input["symbol"], {}).get("quote", {})
            return {
                "symbol": tool_input["symbol"],
                "last": q.get("lastPrice"),
                "bid": q.get("bidPrice"),
                "ask": q.get("askPrice"),
                "mark": q.get("mark"),
                "change_pct": round(
                    (q.get("lastPrice", 0) - q.get("openPrice", 0)) / q.get("openPrice", 1) * 100, 2
                ) if q.get("openPrice") else None,
            }

        if name == "get_option_chain":
            chain = await schwab_client.get_option_chain(
                tool_input["symbol"],
                min_dte=tool_input.get("min_dte", 20),
                max_dte=tool_input.get("max_dte", 60),
                contract_type=tool_input.get("contract_type", "PUT"),
            )
            # Flatten to list of strikes for agent readability
            exp_map = chain.get(
                "putExpDateMap" if tool_input.get("contract_type", "PUT") == "PUT" else "callExpDateMap",
                {},
            )
            strikes = []
            for exp_key, strike_map in list(exp_map.items())[:3]:  # limit to 3 expiries
                exp_date = exp_key.split(":")[0]
                dte = exp_key.split(":")[1] if ":" in exp_key else "?"
                for strike_price, contracts in list(strike_map.items())[:8]:  # limit strikes
                    c = contracts[0] if contracts else {}
                    strikes.append({
                        "expiration": exp_date, "dte": dte, "strike": strike_price,
                        "bid": c.get("bid"), "ask": c.get("ask"), "mark": c.get("mark"),
                        "delta": c.get("delta"), "iv": c.get("volatility"), "oi": c.get("openInterest"),
                    })
            return {
                "symbol": tool_input["symbol"],
                "contract_type": tool_input.get("contract_type", "PUT"),
                "strikes": strikes,
            }

        if name == "get_iv_rank":
            from app.schwab.iv_rank import iv_rank_tracker
            rank = iv_rank_tracker.get_rank(tool_input["symbol"])
            return {
                "symbol": tool_input["symbol"],
                "iv_rank": rank,
                "note": "null means not yet computed — trigger a scan first",
            }

    except Exception as exc:
        logger.error("Market data tool handler error", tool=name, error=str(exc))
        return {"error": str(exc)}

    return None
