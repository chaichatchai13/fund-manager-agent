# Research Skill

Provides web search and stock-specific news retrieval to support trading decisions.

Delegates to `app.services.research_service` (implementation pending).

## Tools

### `web_search`
Search the web for any stock-related information.

**Input:**
- `query` (required) — e.g. `"TSLA earnings Q1 2026 analyst targets"`, `"NVDA guidance cut"`
- `count`: number of results (default 5, max 10)

**Use cases:**
- Analyst price targets and upgrades/downgrades
- Earnings dates and estimates
- Macro news that could affect positions
- Sector rotation signals

### `search_stock_news`
Fetch recent news articles for a specific ticker.

**Input:**
- `symbol` (required) — e.g. `"IREN"`, `"TSLA"`
- `days_back`: how many days back to search (default 7)

**Returns:** list of news articles with title, source, date, and summary.

## When to use
- Before creating a rule for a new symbol: check for upcoming earnings or catalysts
- When a position moves unexpectedly: search for breaking news
- For weekly portfolio review: check news on all held underlyings
- Prefer this skill over training-data knowledge for current events (cutoff: August 2025)
