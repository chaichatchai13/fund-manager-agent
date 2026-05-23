# Market Data Skill

Provides real-time market data via the Schwab API.

## Tools

### `get_quote`
Fetches a live quote for a single stock symbol.

**Input:** `symbol` (string)

**Returns:**
```json
{
  "symbol": "TSLA",
  "last": 285.40,
  "bid": 285.30,
  "ask": 285.50,
  "mark": 285.40,
  "change_pct": -1.23
}
```

### `get_option_chain`
Fetches the live option chain for a symbol across up to 3 expiry dates.

**Input:**
- `symbol` (required)
- `contract_type`: `PUT` or `CALL` (default `PUT`)
- `min_dte`: minimum days to expiration (default 20)
- `max_dte`: maximum days to expiration (default 60)

**Returns:** list of strike objects with `expiration`, `dte`, `strike`, `bid`, `ask`, `mark`, `delta`, `iv`, `oi`.

### `get_iv_rank`
Returns the current IV rank (0–100) for a symbol.

**Input:** `symbol`

**Returns:**
```json
{
  "symbol": "IREN",
  "iv_rank": 72,
  "note": "null means not yet computed — trigger a scan first"
}
```

Higher IV rank = options are relatively expensive = better time to sell premium.

## Notes
- Data comes directly from Schwab — requires a connected Schwab token
- Option chain is truncated to 3 expiries × 8 strikes for readability; raw chain available via Schwab API directly
- IV rank is computed from intraday snapshots collected during scans; it may be null for tickers that haven't been scanned yet
