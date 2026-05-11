"""
Schwab OAuth2 authentication using schwab-py.

schwab-py handles token storage/refresh automatically when using easy_client().
The token is saved to SCHWAB_TOKEN_PATH on first auth and reloaded on subsequent starts.
"""
import schwab
from app.config import settings


def create_schwab_client():
    """Create an authenticated Schwab API client (synchronous — run via asyncio.to_thread)."""
    client = schwab.auth.easy_client(
        api_key=settings.schwab_app_key,
        app_secret=settings.schwab_app_secret,
        callback_url=settings.schwab_callback_url,
        token_path=settings.schwab_token_path,
    )
    return client
