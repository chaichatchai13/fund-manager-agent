#!/bin/sh
set -e

# Ensure schwab_token.json exists as a file (prevents Docker bind-mount creating it as a dir)
if [ ! -f "/app/schwab_token.json" ]; then
    echo "{}" > /app/schwab_token.json
fi

echo "▶ Checking database schema..."

# On a fresh PostgreSQL database there is no alembic_version table.
# In that case: create all tables via SQLAlchemy ORM (gives us the full current schema),
# then stamp alembic to HEAD so future `alembic upgrade head` runs only new migrations.
# On an existing database: just run incremental migrations as normal.
EXIT_CODE=0
python - <<'PYEOF' || EXIT_CODE=$?
import asyncio, sys
from sqlalchemy import text
from app.database import engine, create_tables

async def main():
    async with engine.connect() as conn:
        result = await conn.execute(text(
            "SELECT EXISTS("
            "  SELECT 1 FROM information_schema.tables"
            "  WHERE table_name='alembic_version'"
            ")"
        ))
        has_alembic = result.scalar()

    if not has_alembic:
        print("Fresh database — creating full schema via ORM...")
        await create_tables()
        print("Schema created.")
        sys.exit(42)   # sentinel: caller should stamp head
    else:
        print("Existing database — will run incremental migrations.")
        sys.exit(0)

asyncio.run(main())
PYEOF

if [ "$EXIT_CODE" -eq 42 ]; then
    echo "▶ Stamping alembic to current head (fresh DB)..."
    alembic stamp head
elif [ "$EXIT_CODE" -ne 0 ]; then
    echo "Schema check failed (exit $EXIT_CODE)" >&2
    exit "$EXIT_CODE"
else
    echo "▶ Running incremental Alembic migrations..."
    alembic upgrade head
fi

echo "▶ Starting ThetaFlow..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
