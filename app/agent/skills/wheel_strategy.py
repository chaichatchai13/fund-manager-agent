"""
Wheel strategy skill — Sell Put + Covered Call rule management, position management,
order history, performance analytics, scheduler config, and scan triggers.

All existing tools from app/agent/tools.py live here.
"""
import json
from datetime import date
from typing import Any

import structlog
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.position import OptionPosition
from app.models.rule import SellPutRule
from app.models.scheduler import SchedulerConfig

logger = structlog.get_logger(__name__)

# ── Tool schema definitions (Anthropic format) ────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "name": "list_rules",
        "description": "List all trading rules (both Sell Put and Covered Call) with their current settings and status.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "create_rule",
        "description": (
            "Create a new trading rule for either Sell Put or Covered Call strategy. "
            "strategy_type must be 'SELL_PUT' or 'SELL_COVERED_CALL'. "
            "For premium: use min_premium_mode='pct' with min_premium_pct (% of stock price, e.g. 5.0 = 5%) "
            "OR min_premium_mode='dollar' with min_premium_dollar (fixed $ amount, e.g. 2.0). "
            "For position size: use position_size_mode='pct' with position_size_pct (fraction of buying power, e.g. 0.05 = 5%) "
            "OR position_size_mode='contracts' with position_size_contracts (fixed integer count). "
            "Covered calls require 100 shares per contract; position_size_contracts is capped by shares_owned ÷ 100."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Rule name, e.g. 'IREN Covered Call'"},
                "strategy_type": {
                    "type": "string",
                    "enum": ["SELL_PUT", "SELL_COVERED_CALL"],
                    "description": "SELL_PUT = sell cash-secured puts; SELL_COVERED_CALL = sell calls against existing shares",
                    "default": "SELL_PUT",
                },
                "symbols": {
                    "type": "array",
                    "items": {"type": "object", "properties": {"symbol": {"type": "string"}, "priority": {"type": "integer"}}, "required": ["symbol", "priority"]},
                    "description": "List of {symbol, priority} entries. Lower priority number = traded first.",
                },
                "min_dte": {"type": "integer", "default": 30},
                "max_dte": {"type": "integer", "default": 45},
                # Premium settings
                "min_premium_mode": {
                    "type": "string", "enum": ["pct", "dollar"], "default": "pct",
                    "description": "'pct' = % of stock price; 'dollar' = fixed $ amount",
                },
                "min_premium_pct": {"type": "number", "description": "Min premium as % of stock price (used when mode='pct'). E.g. 5.0 = 5%"},
                "min_premium_dollar": {"type": "number", "description": "Min premium in $ (used when mode='dollar'). E.g. 2.0 = $2.00"},
                "max_premium_pct": {"type": "number", "description": "Optional upper bound on premium % of stock price"},
                # Filters
                "min_daily_drop_pct": {"type": "number", "description": "Only scan if stock drops >= X% today. Null = always scan. Only applies to SELL_PUT."},
                "max_daily_drop_pct": {"type": "number"},
                # Profit management
                "profit_target_pct": {"type": "number", "description": "Close at X% profit, e.g. 0.75 = 75%", "default": 0.75},
                "profit_approach_pct": {"type": "number", "description": "Place advance GTC order when unrealized profit reaches this %. E.g. 0.60"},
                "stop_loss_pct": {"type": "number", "description": "Close if current price >= entry × stop_loss_pct. E.g. 2.0"},
                # Position sizing
                "max_open_positions": {"type": "integer", "default": 5},
                "position_size_mode": {
                    "type": "string", "enum": ["pct", "contracts"], "default": "pct",
                    "description": "'pct' = % of buying power (SELL_PUT) or % of available contracts (SELL_COVERED_CALL); 'contracts' = fixed count",
                },
                "position_size_pct": {"type": "number", "description": "Fraction of buying power per trade, e.g. 0.05 = 5% (used when mode='pct')"},
                "position_size_contracts": {"type": "integer", "description": "Fixed number of contracts (used when mode='contracts'). Capped by shares ÷ 100 for covered calls."},
                "max_position_size_usd": {"type": "number"},
                "scan_interval_minutes": {"type": "integer", "default": 15},
            },
            "required": ["name", "symbols"],
        },
    },
    {
        "name": "update_rule",
        "description": "Update fields on an existing trading rule. Supports all fields from create_rule.",
        "input_schema": {
            "type": "object",
            "properties": {
                "rule_id": {"type": "string"},
                "name": {"type": "string"},
                "enabled": {"type": "boolean"},
                "strategy_type": {"type": "string", "enum": ["SELL_PUT", "SELL_COVERED_CALL"]},
                "symbols": {"type": "array"},
                "min_dte": {"type": "integer"},
                "max_dte": {"type": "integer"},
                "min_premium_mode": {"type": "string", "enum": ["pct", "dollar"]},
                "min_premium_pct": {"type": "number"},
                "min_premium_dollar": {"type": "number"},
                "max_premium_pct": {"type": "number"},
                "min_daily_drop_pct": {"type": "number"},
                "max_daily_drop_pct": {"type": "number"},
                "profit_target_pct": {"type": "number"},
                "profit_approach_pct": {"type": "number"},
                "stop_loss_pct": {"type": "number"},
                "max_open_positions": {"type": "integer"},
                "position_size_mode": {"type": "string", "enum": ["pct", "contracts"]},
                "position_size_pct": {"type": "number"},
                "position_size_contracts": {"type": "integer"},
                "max_position_size_usd": {"type": "number"},
                "scan_interval_minutes": {"type": "integer"},
            },
            "required": ["rule_id"],
        },
    },
    {
        "name": "enable_rule",
        "description": "Enable a sell put rule.",
        "input_schema": {"type": "object", "properties": {"rule_id": {"type": "string"}}, "required": ["rule_id"]},
    },
    {
        "name": "disable_rule",
        "description": "Disable a sell put rule (stops scanning but doesn't close positions).",
        "input_schema": {"type": "object", "properties": {"rule_id": {"type": "string"}}, "required": ["rule_id"]},
    },
    {
        "name": "delete_rule",
        "description": "Delete a sell put rule.",
        "input_schema": {"type": "object", "properties": {"rule_id": {"type": "string"}}, "required": ["rule_id"]},
    },
    {
        "name": "list_positions",
        "description": "List option positions. Filter by status: OPEN, CLOSING, CLOSED, or ALL.",
        "input_schema": {
            "type": "object",
            "properties": {"status": {"type": "string", "enum": ["OPEN", "CLOSING", "CLOSED", "ALL"], "default": "OPEN"}},
            "required": [],
        },
    },
    {
        "name": "get_position_detail",
        "description": "Get full details for a specific position including entry Greeks and current P&L.",
        "input_schema": {"type": "object", "properties": {"position_id": {"type": "string"}}, "required": ["position_id"]},
    },
    {
        "name": "manually_close_position",
        "description": "Manually close a position by placing a buy-to-close order at a specified limit price.",
        "input_schema": {
            "type": "object",
            "properties": {
                "position_id": {"type": "string"},
                "limit_price": {"type": "number", "description": "Limit price for the BTC order. Defaults to current mid price."},
            },
            "required": ["position_id"],
        },
    },
    {
        "name": "list_orders",
        "description": "List recent orders. Optionally filter by status.",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "e.g. WORKING, FILLED, CANCELLED"},
                "limit": {"type": "integer", "default": 20},
            },
            "required": [],
        },
    },
    {
        "name": "get_performance_summary",
        "description": "Get P&L performance summary for a period.",
        "input_schema": {
            "type": "object",
            "properties": {"period": {"type": "string", "enum": ["today", "week", "month", "all_time"]}},
            "required": ["period"],
        },
    },
    {
        "name": "get_daily_pnl",
        "description": "Get daily P&L series between two dates.",
        "input_schema": {
            "type": "object",
            "properties": {
                "start_date": {"type": "string", "description": "ISO date, e.g. 2026-01-01"},
                "end_date": {"type": "string", "description": "ISO date, e.g. 2026-04-12"},
            },
            "required": ["start_date", "end_date"],
        },
    },
    {
        "name": "get_trade_history",
        "description": "Get closed trade history with realized P&L per trade.",
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Filter by underlying symbol. Optional."},
                "limit": {"type": "integer", "default": 20},
            },
            "required": [],
        },
    },
    {
        "name": "scan_now",
        "description": "Trigger an immediate scan for trading opportunities (Sell Put or Covered Call, depending on the rule).",
        "input_schema": {
            "type": "object",
            "properties": {"rule_id": {"type": "string", "description": "Scan only this rule. Omit to scan all enabled rules."}},
            "required": [],
        },
    },
    {
        "name": "get_account_summary",
        "description": "Get current account balances: portfolio value, buying power, cash.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_scheduler_config",
        "description": "Get current scheduler job configurations (intervals, enabled status).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "update_job_interval",
        "description": "Update the interval for a scheduler job.",
        "input_schema": {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "enum": ["scan_job", "profit_check_job", "order_status_job"]},
                "interval_minutes": {"type": "integer"},
                "max_runtime_minutes": {"type": "integer", "description": "Only for order_status_job. How many minutes to poll after an order is placed."},
            },
            "required": ["job_id", "interval_minutes"],
        },
    },
]


# ── Tool handlers ─────────────────────────────────────────────────────────────

_HANDLER_MAP = {
    "list_rules": "_list_rules",
    "create_rule": "_create_rule",
    "update_rule": "_update_rule",
    "enable_rule": "_enable_disable_rule",
    "disable_rule": "_enable_disable_rule",
    "delete_rule": "_delete_rule",
    "list_positions": "_list_positions",
    "get_position_detail": "_get_position_detail",
    "manually_close_position": "_manually_close_position",
    "list_orders": "_list_orders",
    "get_performance_summary": "_get_performance_summary",
    "get_daily_pnl": "_get_daily_pnl",
    "get_trade_history": "_get_trade_history",
    "scan_now": "_scan_now",
    "get_account_summary": "_get_account_summary",
    "get_scheduler_config": "_get_scheduler_config",
    "update_job_interval": "_update_job_interval",
}

_TOOL_NAMES = set(_HANDLER_MAP.keys())


async def handle_tool_call(tool_name: str, tool_input: dict[str, Any]) -> Any:
    """Handle a wheel-strategy tool call. Returns None if tool_name is not owned by this skill."""
    if tool_name not in _TOOL_NAMES:
        return None
    func_name = _HANDLER_MAP[tool_name]
    handler = globals()[func_name]
    try:
        return await handler(tool_name, tool_input)
    except Exception as exc:
        logger.error("Wheel strategy tool handler error", tool=tool_name, error=str(exc))
        return {"error": str(exc)}


async def _list_rules(_: str, __: dict) -> list:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SellPutRule).order_by(SellPutRule.created_at))
        rules = result.scalars().all()
    return [
        {
            "id": r.id, "name": r.name, "enabled": r.enabled,
            "strategy_type": getattr(r, "strategy_type", "SELL_PUT"),
            "symbols": r.symbols, "min_dte": r.min_dte, "max_dte": r.max_dte,
            "min_premium_mode": getattr(r, "min_premium_mode", "pct"),
            "min_premium_pct": r.min_premium_pct,
            "min_premium_dollar": getattr(r, "min_premium_dollar", None),
            "max_premium_pct": r.max_premium_pct,
            "min_daily_drop_pct": r.min_daily_drop_pct, "max_daily_drop_pct": r.max_daily_drop_pct,
            "profit_target_pct": r.profit_target_pct, "profit_approach_pct": r.profit_approach_pct,
            "stop_loss_pct": r.stop_loss_pct,
            "max_open_positions": r.max_open_positions,
            "position_size_mode": getattr(r, "position_size_mode", "pct"),
            "position_size_pct": r.position_size_pct,
            "position_size_contracts": getattr(r, "position_size_contracts", None),
            "scan_interval_minutes": r.scan_interval_minutes,
        }
        for r in rules
    ]


async def _create_rule(_: str, inp: dict) -> dict:
    from app.models.rule import SellPutRule
    strategy_type = inp.get("strategy_type", "SELL_PUT")
    min_premium_mode = inp.get("min_premium_mode", "pct")
    position_size_mode = inp.get("position_size_mode", "pct")

    rule = SellPutRule(
        name=inp["name"],
        strategy_type=strategy_type,
        symbols=inp.get("symbols", []),
        min_dte=inp.get("min_dte", 30),
        max_dte=inp.get("max_dte", 45),
        min_premium_mode=min_premium_mode,
        min_premium_pct=inp.get("min_premium_pct", 1.0),
        min_premium_dollar=inp.get("min_premium_dollar") if min_premium_mode == "dollar" else None,
        max_premium_pct=inp.get("max_premium_pct"),
        min_daily_drop_pct=inp.get("min_daily_drop_pct") if strategy_type == "SELL_PUT" else None,
        max_daily_drop_pct=inp.get("max_daily_drop_pct") if strategy_type == "SELL_PUT" else None,
        profit_target_pct=inp.get("profit_target_pct", 0.75),
        profit_approach_pct=inp.get("profit_approach_pct"),
        stop_loss_pct=inp.get("stop_loss_pct"),
        max_open_positions=inp.get("max_open_positions", 5),
        position_size_mode=position_size_mode,
        position_size_pct=inp.get("position_size_pct", 0.05),
        position_size_contracts=inp.get("position_size_contracts") if position_size_mode == "contracts" else None,
        max_position_size_usd=inp.get("max_position_size_usd"),
        scan_interval_minutes=inp.get("scan_interval_minutes", 15),
    )
    async with AsyncSessionLocal() as db:
        db.add(rule)
        await db.commit()
        await db.refresh(rule)
    return {"id": rule.id, "message": f"Rule '{rule.name}' created — strategy: {strategy_type}"}


async def _update_rule(_: str, inp: dict) -> dict:
    rule_id = inp.pop("rule_id")
    async with AsyncSessionLocal() as db:
        rule = await db.get(SellPutRule, rule_id)
        if not rule:
            return {"error": "Rule not found"}
        for field, value in inp.items():
            if hasattr(rule, field) and value is not None:
                setattr(rule, field, value)
        await db.commit()
    return {"message": f"Rule {rule_id} updated"}


async def _enable_disable_rule(tool_name: str, inp: dict) -> dict:
    rule_id = inp["rule_id"]
    enabled = tool_name == "enable_rule"
    async with AsyncSessionLocal() as db:
        rule = await db.get(SellPutRule, rule_id)
        if not rule:
            return {"error": "Rule not found"}
        rule.enabled = enabled
        await db.commit()
    return {"message": f"Rule {rule_id} {'enabled' if enabled else 'disabled'}"}


async def _delete_rule(_: str, inp: dict) -> dict:
    async with AsyncSessionLocal() as db:
        rule = await db.get(SellPutRule, inp["rule_id"])
        if not rule:
            return {"error": "Rule not found"}
        await db.delete(rule)
        await db.commit()
    return {"message": "Rule deleted"}


async def _list_positions(_: str, inp: dict) -> list:
    status_filter = inp.get("status", "OPEN")
    async with AsyncSessionLocal() as db:
        query = select(OptionPosition).order_by(OptionPosition.opened_at.desc())
        if status_filter != "ALL":
            query = query.where(OptionPosition.status == status_filter)
        result = await db.execute(query)
        positions = result.scalars().all()

    return [
        {
            "id": p.id, "underlying": p.underlying_symbol, "option_symbol": p.option_symbol,
            "strike": p.strike, "expiration": str(p.expiration_date), "dte_at_entry": p.dte_at_entry,
            "contracts": p.contracts, "premium_received": p.premium_received,
            "total_credit": p.total_credit, "current_price": p.current_price,
            "unrealized_pnl": p.unrealized_pnl, "status": p.status,
            "opened_at": str(p.opened_at),
        }
        for p in positions
    ]


async def _get_position_detail(_: str, inp: dict) -> dict:
    async with AsyncSessionLocal() as db:
        position = await db.get(OptionPosition, inp["position_id"])
    if not position:
        return {"error": "Position not found"}
    return {
        "id": position.id, "underlying": position.underlying_symbol,
        "option_symbol": position.option_symbol, "strike": position.strike,
        "expiration": str(position.expiration_date), "dte_at_entry": position.dte_at_entry,
        "delta_at_entry": position.delta_at_entry, "iv_rank_at_entry": position.iv_rank_at_entry,
        "stock_price_at_entry": position.stock_price_at_entry,
        "contracts": position.contracts, "premium_received": position.premium_received,
        "total_credit": position.total_credit, "current_price": position.current_price,
        "unrealized_pnl": position.unrealized_pnl, "status": position.status,
        "entry_order_id": position.entry_order_id, "exit_order_id": position.exit_order_id,
        "opened_at": str(position.opened_at), "closed_at": str(position.closed_at) if position.closed_at else None,
    }


async def _manually_close_position(_: str, inp: dict) -> dict:
    position_id = inp["position_id"]
    async with AsyncSessionLocal() as db:
        position = await db.get(OptionPosition, position_id)
    if not position:
        return {"error": "Position not found"}
    if position.status not in ("OPEN", "CLOSING"):
        return {"error": f"Position status is {position.status}, cannot close"}

    limit_price = inp.get("limit_price") or position.current_price or position.premium_received * 0.25
    limit_price = round(float(limit_price), 2)

    from app.services.order_manager import order_manager
    from app.services.position_manager import position_manager
    order = await order_manager.place_buy_to_close(
        option_symbol=position.option_symbol,
        quantity=position.contracts,
        limit_price=limit_price,
        position_id=position_id,
    )
    await position_manager.mark_closing(position_id, order.id)
    return {"message": f"BTC order placed at ${limit_price}", "order_id": order.id}


async def _list_orders(_: str, inp: dict) -> list:
    from app.models.order import Order
    from sqlalchemy import select
    limit = inp.get("limit", 20)
    status_filter = inp.get("status")
    async with AsyncSessionLocal() as db:
        query = select(Order).order_by(Order.created_at.desc()).limit(limit)
        if status_filter:
            query = query.where(Order.status == status_filter)
        result = await db.execute(query)
        orders = result.scalars().all()
    return [
        {"id": o.id, "schwab_order_id": o.schwab_order_id, "type": o.order_type,
         "status": o.status, "symbol": o.symbol, "qty": o.quantity,
         "limit_price": o.limit_price, "fill_price": o.fill_price,
         "is_gtc": o.is_gtc, "created_at": str(o.created_at)}
        for o in orders
    ]


async def _get_performance_summary(_: str, inp: dict) -> dict:
    from app.services.performance_tracker import performance_tracker
    summary = await performance_tracker.get_summary(inp["period"])
    return summary.model_dump()


async def _get_daily_pnl(_: str, inp: dict) -> list:
    from app.services.performance_tracker import performance_tracker
    start = date.fromisoformat(inp["start_date"])
    end = date.fromisoformat(inp["end_date"])
    snapshots = await performance_tracker.get_daily_series(start, end)
    return [s.model_dump() for s in snapshots]


async def _get_trade_history(_: str, inp: dict) -> list:
    from app.services.performance_tracker import performance_tracker
    trades = await performance_tracker.get_trade_history(
        symbol=inp.get("symbol"), limit=inp.get("limit", 20)
    )
    return [t.model_dump() for t in trades]


async def _scan_now(_: str, inp: dict) -> dict:
    from app.services.scan_service import scan_service
    rule_id = inp.get("rule_id")
    position_ids = await scan_service.run_scan(rule_id=rule_id)
    return {
        "positions_created": len(position_ids),
        "position_ids": position_ids,
        "message": f"Scan complete — {len(position_ids)} position(s) opened",
    }


async def _get_account_summary(_: str, __: dict) -> dict:
    from app.schwab.client import schwab_client
    account = await schwab_client.get_account()
    balances = account.get("securitiesAccount", {}).get("currentBalances", {})
    return {
        "portfolio_value": balances.get("liquidationValue"),
        "buying_power": balances.get("buyingPower"),
        "cash_balance": balances.get("cashBalance"),
    }


async def _get_scheduler_config(_: str, __: dict) -> list:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SchedulerConfig))
        configs = result.scalars().all()
    return [
        {"job_id": c.job_id, "interval_minutes": c.interval_minutes,
         "max_runtime_minutes": c.max_runtime_minutes, "enabled": c.enabled}
        for c in configs
    ]


async def _update_job_interval(_: str, inp: dict) -> dict:
    job_id = inp["job_id"]
    interval_minutes = inp["interval_minutes"]
    max_runtime = inp.get("max_runtime_minutes")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(SchedulerConfig).where(SchedulerConfig.job_id == job_id))
        config = result.scalar_one_or_none()
        if config:
            config.interval_minutes = interval_minutes
            if max_runtime is not None:
                config.max_runtime_minutes = max_runtime
            await db.commit()

    # Reschedule live
    from app.scheduler.jobs import reschedule_job
    await reschedule_job(job_id, interval_minutes)

    return {"message": f"Job '{job_id}' updated to every {interval_minutes} minutes"}
