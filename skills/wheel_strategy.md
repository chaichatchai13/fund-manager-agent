# Wheel Strategy Skill

Automates the sell-put / covered-call options income wheel using rules configured by the user.

## Tools

### `list_rules`
Returns all trading rules with their full configuration (strategy type, symbols, premium filters, profit targets, position sizing).

### `create_rule`
Creates a new rule. Key parameters:
- `strategy_type`: `SELL_PUT` or `SELL_COVERED_CALL`
- `symbols`: list of `{symbol, priority}` — lower priority number traded first
- `min_premium_mode`: `pct` (% of stock price) or `dollar` (fixed $ amount)
- `position_size_mode`: `pct` (fraction of buying power) or `contracts` (fixed count)
- `profit_target_pct`: e.g. `0.75` = close at 75% profit

### `update_rule`
Updates any field on an existing rule by `rule_id`.

### `enable_rule` / `disable_rule`
Toggle scanning for a rule without deleting it.

### `delete_rule`
Permanently removes a rule.

### `list_positions`
Lists option positions filtered by status: `OPEN`, `CLOSING`, `CLOSED`, or `ALL`.

### `get_position_detail`
Full position details including entry Greeks (delta, IV rank), stock price at entry, order IDs.

### `manually_close_position`
Places a BTC (buy-to-close) limit order for an open position. Defaults to current mark price.

### `list_orders`
Recent orders with fill prices, status, and timestamps.

### `get_performance_summary`
Aggregated P&L for `today`, `week`, `month`, or `all_time`.

### `get_daily_pnl`
Daily P&L time series between two ISO dates.

### `get_trade_history`
Closed trade history with realized P&L per position. Optionally filter by symbol.

### `scan_now`
Triggers an immediate scan for sell-put or covered-call opportunities. Optionally scoped to one rule.

### `get_account_summary`
Live account balances: portfolio value, buying power, cash.

### `get_scheduler_config`
Current job intervals (scan, profit-check, order-status).

### `update_job_interval`
Change how often a scheduler job runs.

## Position sizing formulas

**Sell Put:**
```
contracts = floor((buying_power × position_size_pct) / (strike × 100))
```

**Covered Call:**
```
contracts = floor(shares_owned / 100)   # capped by position_size_pct if mode=pct
```

## Option symbol format
DB stores underscores: `IREN_260508C00048000`
Schwab returns spaces: `IREN 260508C00048000`
Always normalise with `.replace(" ", "_").upper()`.
