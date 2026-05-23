# Direct Trading Skill

Allows the agent to place equity and option orders directly outside the automated rules engine.

**Important:** Always confirm the exact order details with the user before calling any tool in this skill.

## Tools

### `buy_shares`
Place a buy order for stock shares.

**Input:**
- `symbol` (required)
- `quantity` (required, integer)
- `order_type`: `MARKET` or `LIMIT` (default `LIMIT`)
- `limit_price`: required when `order_type=LIMIT`

### `sell_shares`
Place a sell order for stock shares.

Same parameters as `buy_shares`.

### `buy_option`
Buy to open a call or put option.

**Input:**
- `option_symbol` (required) — OCC format with underscores, e.g. `TSLA_260620C00300000`
- `contracts` (required, integer)
- `order_type`: `MARKET` or `LIMIT` (default `LIMIT`)
- `limit_price`: required for limit orders

### `sell_option_manual`
Sell to open a single option contract manually (not tracked by the automated rules system).

Same parameters as `buy_option`.

**Note:** `buy_option` and `sell_option_manual` return a placeholder error until full implementation is complete in the next sprint. Use `create_rule` + `scan_now` for automated option selling.

## OCC Symbol Format
```
UNDERLYING + YYMMDD + C/P + strike×1000 (8 digits zero-padded)

Examples:
  TSLA_260620C00300000   = TSLA $300 call expiring 2026-06-20
  IREN_260508P00048000   = IREN $48 put expiring 2026-05-08
```
