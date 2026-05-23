# Social Intel Skill

Tracks X (Twitter) accounts for trading signals, unusual options flow commentary, and market sentiment.

Delegates to `app.services.social_service` (implementation pending).

## Tools

### `get_social_watchlist`
Returns all X accounts currently being watched and their associated stock tickers.

**Input:** none

**Returns:**
```json
[
  {"x_handle": "unusual_whales", "stocks": ["SPY", "TSLA", "NVDA"]},
  {"x_handle": "thestreet", "stocks": ["IREN"]}
]
```

### `add_social_watchlist`
Add an X account to the watchlist, associated with specific tickers.

**Input:**
- `x_handle` (required) — without the `@`, e.g. `"unusual_whales"`
- `stocks` (required) — list of ticker symbols to track for this account, e.g. `["TSLA", "NVDA"]`

### `get_social_summary`
Get a summary of recent posts from watched accounts, optionally filtered to specific tickers.

**Input:**
- `stocks`: list of tickers to filter by. Empty list = all watched stocks.
- `since_last_check`: if true (default), only return posts since the last summary was requested

**Returns:** per-ticker summary of relevant posts with sentiment signals.

## Recommended accounts to watch
- `unusual_whales` — unusual options flow and dark pool activity
- `optionsmillionaire` — options trade ideas
- `marketwatch` / `thestreet` — breaking news
- Sector-specific analysts and fund managers relevant to your holdings

## Notes
- This skill surfaces social signals only — never place orders based on social data alone
- Always cross-reference with `web_search` or `search_stock_news` before acting on a signal
