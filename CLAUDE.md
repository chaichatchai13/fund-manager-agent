# ThetaFlow — Claude Code Guide

Automated sell-puts / covered-call wheel trading system on top of the Schwab API.
Backend: FastAPI + SQLAlchemy async (SQLite dev). Frontend: React + Vite + TypeScript.
Agent interface: Claude claude-sonnet-4-6 with tool-use loop.

---

## Dev Commands

```bash
# Backend (runs on http://localhost:8000)
poetry run uvicorn main:app --reload --port 8000

# Frontend (runs on http://localhost:5173, proxies /api → 8000)
cd frontend && npm run dev

# Run both together (open two terminals)

# Database migrations
poetry run alembic upgrade head          # apply all pending migrations
poetry run alembic revision --autogenerate -m "description"  # generate new migration

# Schwab OAuth (first-time setup or token expired)
poetry run python setup_schwab_auth.py

# Tests
poetry run pytest tests/ -v
```

### Python / Poetry rules
- **Python 3.12 only** — `pyproject.toml` requires `^3.12`. Never change to 3.13+.
- **Always use Poetry** — never `pip install`. If a package is missing: `poetry add <pkg>`.
- If the app fails with `No such file or directory: 'python'`, run:
  `poetry env use python3.12 && poetry install`

---

## Mock Mode (local dev without Schwab)

Set `MOCK_SCHWAB=true` in `.env`. This swaps `SchwabClient` for `MockSchwabClient` globally — do not mock individual methods. The mock:
- Returns canned option chain fixtures
- Logs orders to stdout instead of sending them to Schwab
- Never touches `schwab_token.json`

Real credentials live in `.env` (`SCHWAB_APP_KEY`, `SCHWAB_APP_SECRET`) and `schwab_token.json`. Never commit either file.

---

## Architecture Rules

### Database sessions
Always use the context manager pattern — never pass sessions across function boundaries:
```python
async with AsyncSessionLocal() as db:
    result = await db.execute(...)
```
`get_db` (FastAPI dependency) is only for route handlers. Services open their own sessions.

### Schwab is the single source of truth
The DB holds metadata Schwab doesn't know: rule_id, entry premium, profit targets, status history.
Whether a position *exists* is always determined by the live Schwab account, not the DB.
- Positions missing from Schwab → reconciler marks them CLOSED / EXPIRED / deletes phantoms
- Never trust `status == "OPEN"` in the DB as proof the position is live

### Phantom position prevention
`scan_service.py` polls order status 3 seconds after placing a sell-to-open. If REJECTED or CANCELLED, it skips position creation entirely. Do not revert this check.

### Option symbol format
Schwab returns symbols with spaces: `IREN 260508C00048000`  
ThetaFlow DB stores them with underscores: `IREN_260508C00048000`  
Always normalise with `.replace(" ", "_").upper()` before comparing.  
Parse strike/expiry/type from the OCC format: `UNDERLYING[YYMMDD][C/P][strike*1000 8-digit]`

### Singletons
These are module-level singletons — never instantiate them directly in calling code:
- `from app.services.roll_manager import roll_manager`
- `from app.services.profit_manager import profit_manager`
- `from app.services.scan_service import scan_service`
- `from app.services.position_reconciler import position_reconciler`
- `from app.schwab.client import schwab_client`
- `from app.schwab.stream_manager import stream_manager`

### Logging
Use `structlog` everywhere. Never use `print()` or the stdlib `logging` module directly:
```python
import structlog
logger = structlog.get_logger(__name__)
logger.info("thing happened", key=value)
```

### Agent message history
The Claude agent is **stateless** — conversation history lives in the React frontend and is sent on every `/api/agent/chat` request. There is no server-side session table. Anthropic SDK response objects must be converted to plain dicts before storing in the message list:
```python
content_dicts = [block.model_dump() for block in response.content]
```

---

## Database & Migrations

- **SQLite in dev** (file: `thetaflow.db`). PostgreSQL-ready via `DATABASE_URL` env var.
- **Always use `batch_alter_table`** in Alembic migrations — SQLite does not support `ALTER COLUMN` directly:
```python
def upgrade() -> None:
    with op.batch_alter_table('sell_put_rules') as batch_op:
        batch_op.add_column(sa.Column('new_col', sa.String(20), nullable=False, server_default='default'))
```
- Migration chain: `base → 002_strategy_type → 003_premium_and_sizing_modes → 004_itm_roll_columns (head)`
- After adding a column to an ORM model, always create a migration — don't rely on `create_all`.

---

## Key Services & What They Own

| Service | Responsibility |
|---|---|
| `scan_service` | Runs RulesEngine → places sell-to-open orders → creates position records |
| `profit_manager` | Monitors open positions for profit target / stop-loss → places BTC orders |
| `roll_manager` | Detects ITM positions past DTE threshold → BTC current, STO new OTM at closest premium |
| `position_reconciler` | Schwab sync: marks CLOSED/EXPIRED/deletes phantoms based on live account |
| `order_manager` | Wraps all order placement + Schwab polling + DB persistence |
| `position_manager` | Creates/updates/closes `OptionPosition` records |
| `performance_tracker` | Daily snapshots + P&L aggregation |

---

## Trading Strategy Reference

### Sell Put
- Scanner finds OTM puts where `mid ≥ stock_price × (min_premium_pct / 100)`
- Strike must be below current stock price (OTM)
- Position size: `contracts = floor((buying_power × size_pct) / (strike × 100))`
- Profit target: buy back at `entry_price × (1 - profit_target_pct)` — e.g. $6.00 × 0.25 = $1.50 for 75% target

### Sell Covered Call
- Requires 100 shares per contract already held
- Position size: `contracts = floor(shares_held / 100)` (capped by `position_size_pct` of shares if mode=pct)
- Same profit target mechanics as sell put

### Roll Logic (ITM management)
1. Detect: position ITM **and** DTE ≤ `rule.roll_when_dte`
2. Buy-to-close current position at current mark
3. Fetch chain for `today + roll_target_weeks × 7 days` (±7 day window)
4. Filter OTM strikes only
5. Pick strike with `mid` closest to original `premium_received`
6. Sell-to-open new position; create new DB record linked to same `rule_id`

ITM definition:
- Short CALL (covered call): `stock_price > strike`
- Short PUT: `stock_price < strike`

---

## Frontend Notes

- Vite dev server proxies `/api/*` and `/ws/*` to `localhost:8000` (see `vite.config.ts`)
- Inline styles only (no CSS files, no Tailwind classes) — keep the dark GitHub-style aesthetic
- Design tokens in `App.tsx`: `BG = '#0d1117'`, `CARD_BG = '#161b22'`, `BORDER = '#30363d'`
- `useWebSocket` hook in `hooks/useWebSocket.ts` owns the live position state — always update via `setPositions`, not a separate fetch, when possible
- Types live in `src/types/index.ts` — add fields there first before using them in components

---

## Common Mistakes to Avoid

- **Don't use `poetry run python -m uvicorn`** — use `poetry run uvicorn` directly
- **Don't add columns to ORM models without a migration** — the DB won't update automatically
- **Don't `import asyncio; asyncio.run()` inside an async context** — use `await` directly
- **Don't hardcode `"OPEN"` status checks** to infer a position is live in Schwab — always reconcile
- **Don't store raw Anthropic SDK objects** in message lists — call `.model_dump()` first
- **Don't use `get_db` in services** — only in FastAPI route handlers
- **Don't skip the 3-second poll after order placement** in scan_service — that's what prevents phantom positions
