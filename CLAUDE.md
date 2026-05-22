# ThetaFlow — Claude Code Guide

Automated sell-puts / covered-call wheel trading system on top of the Schwab API.
Backend: FastAPI + SQLAlchemy async + PostgreSQL. Frontend: React + Vite + TypeScript.
Agent interface: Claude claude-sonnet-4-6 with tool-use loop.

---

## Production Deployment Roadmap

Work through these phases in order. Each phase has a clear deliverable before moving on.

| Phase | What it delivers | Status |
|---|---|---|
| **1 — Containerise** | `docker compose up` runs full stack (backend + PostgreSQL + Caddy) | ✅ Done |
| **2 — Auth layer** | Login screen + JWT middleware — app protected before going public | ✅ Done |
| **3 — Schwab connection UI** | Reconnect Schwab from browser, no SSH needed | ✅ Done |
| **4 — PWA** | ThetaFlow icon on iPhone home screen, fullscreen app feel | ✅ Done |
| **5 — GCP deploy** | Live at `https://yourdomain.com`, accessible from phone anywhere | ✅ Done |

### Phase 1 — Containerise ✅
Files created: `Dockerfile`, `docker-compose.yml`, `Caddyfile`, `docker-entrypoint.sh`, `.env.example`, `.dockerignore`

Key decisions made:
- Multi-stage Docker build: Node 20 builds React frontend, Python 3.12-slim runs backend
- Dependencies installed via `poetry export` → `pip install` (no venv inside container)
- `docker-entrypoint.sh` detects fresh vs existing DB: fresh → `create_tables()` + `alembic stamp head`; existing → `alembic upgrade head`
- Caddy handles automatic HTTPS via Let's Encrypt using `THETAFLOW_DOMAIN` env var
- `schwab_token.json` bind-mounted from host (runtime secret, never baked into image)

To run locally:
```bash
cp .env.example .env          # fill in SCHWAB_*, ANTHROPIC_API_KEY, DB_PASS
# Set THETAFLOW_DOMAIN=localhost in .env for local testing
docker compose up --build
```

### Phase 2 — Auth Layer ⬜
Plan:
- `POST /auth/login` — verify `THETAFLOW_PASSWORD` env var (bcrypt), set JWT in HttpOnly cookie (7-day expiry)
- `POST /auth/logout` — clear cookie
- `GET /auth/me` — return current user info
- FastAPI middleware — validates JWT on all `/api/*` and `/ws/*` routes; returns 401 if missing/expired
- React login page — shown when 401 received; redirects back to original URL after login
- Designed for single user now; adding a `users` table later enables multi-user without breaking changes

### Phase 3 — Schwab Connection UI ✅
Files created/changed: `app/models/schwab_token.py`, `app/schwab/token_store.py`, `alembic/versions/005_schwab_tokens.py`, `app/api/routes/schwab.py`, `app/schwab/client.py`, `frontend/src/components/SettingsPanel.tsx`

Key decisions:
- `schwab_tokens` table stores one row (id=1) with Fernet-encrypted token JSON
- Fernet key derived from `SECRET_KEY` via SHA-256 — no extra env var needed
- On startup: if token file exists → seed DB from file; if only DB → write file → init schwab-py
- Token format: `{"creation_timestamp": <unix>, "token": {...oauth fields...}}` — matches schwab-py
- OAuth endpoints on `/api/schwab/*` (not `/auth/schwab/*`) — `/callback` and `/connect` are public paths
- Settings tab in frontend: shows connection state, token expiry warnings, Reconnect/Refresh/Reinitialize buttons
- `SCHWAB_CALLBACK_URL` in `.env` must be updated to `https://yourdomain.com/api/schwab/callback` and registered in Schwab developer app before OAuth flow works

### Phase 4 — PWA ✅
Files: `frontend/public/manifest.json`, `frontend/public/icon-192.png`, `frontend/public/icon-512.png`, `frontend/public/icon-180.png`, `frontend/index.html`, `frontend/src/index.css`

- Icons generated via Pillow (gradient blue→green background + theta symbol), 512/192/180px
- `manifest.json`: `display: standalone`, `theme_color: #0d1117`, both icon sizes listed
- `index.html`: manifest link, `apple-mobile-web-app-capable`, `apple-touch-icon`, `theme-color`, `viewport-fit=cover`
- `index.css`: `env(safe-area-inset-*)` padding so content clears iPhone notch/Dynamic Island
- To install: Safari → Share → Add to Home Screen → ThetaFlow appears as fullscreen app

### Phase 5 — GCP Deploy ✅
Files: `deploy/setup-vm.sh`, `deploy/thetaflow.service`

Step-by-step:
1. **GCP VM**: e2-small, Debian 12, us-central1. In GCP Console → Compute Engine → VM Instances → Create.
2. **Static IP**: VPC Network → IP Addresses → Reserve external static IP → attach to VM.
3. **Firewall**: VPC Network → Firewall → allow ingress tcp:80,443 from 0.0.0.0/0 (tags: `http-server`, `https-server`).
4. **Domain**: Buy at Namecheap/Cloudflare. Add DNS A record → VM static IP. TTL 300.
5. **SSH into VM**: `gcloud compute ssh INSTANCE_NAME --zone=ZONE`
6. **Run setup script**: `curl -fsSL https://raw.githubusercontent.com/chaichatchai13/fund-manager-agent/main/deploy/setup-vm.sh | bash`
7. **Edit .env**: `nano /opt/thetaflow/.env` — fill in all secrets, set `THETAFLOW_DOMAIN=yourdomain.com`, `ENVIRONMENT=production`
8. **Update Schwab callback**: In Schwab developer app settings, set callback URL to `https://yourdomain.com/api/schwab/callback`
9. **Re-run setup**: `bash /opt/thetaflow/deploy/setup-vm.sh` — installs systemd service, starts app
10. **First HTTPS request**: Caddy auto-issues Let's Encrypt cert on first browser visit
11. **Connect Schwab**: Settings tab → Reconnect via Schwab OAuth

Auto-restart: `systemd` service (`deploy/thetaflow.service`) starts Docker Compose on boot and restarts on crash.

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

- **PostgreSQL everywhere** — local dev uses `docker compose up`, production uses GCP VM. No SQLite.
- DB connection built from `DB_HOST / DB_PORT / DB_NAME / DB_USER / DB_PASS` env vars (see `app/config.py`).
- **Always use `batch_alter_table`** in Alembic migrations for cross-DB compatibility:
```python
def upgrade() -> None:
    with op.batch_alter_table('sell_put_rules') as batch_op:
        batch_op.add_column(sa.Column('new_col', sa.String(20), nullable=False, server_default='default'))
```
- Migration chain: `base → 002_strategy_type → 003_premium_and_sizing_modes → 004_itm_roll_columns (head)`
- After adding a column to an ORM model, always create a migration — don't rely on `create_all`.
- Fresh DB detection: `docker-entrypoint.sh` checks for `alembic_version` table — if missing, runs `create_tables()` then `alembic stamp head` instead of `alembic upgrade head`.

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
