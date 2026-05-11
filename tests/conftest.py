import os
import pytest

# Use in-memory SQLite for tests and mock Schwab
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("MOCK_SCHWAB", "true")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
