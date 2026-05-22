"""
Schwab connection management endpoints.

OAuth flow:
  1. GET  /api/schwab/connect   → redirect browser to Schwab authorize URL
  2. GET  /api/schwab/callback  → exchange code, save token, redirect to /
  3. POST /api/schwab/refresh   → force-refresh access token
  4. GET  /api/schwab/status    → current connection state
  5. POST /api/schwab/reconnect → re-initialize from existing token (file or DB)
"""
import base64
import time

import httpx
import structlog
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from app.config import settings

router = APIRouter(prefix="/api/schwab", tags=["schwab"])
logger = structlog.get_logger(__name__)

SCHWAB_AUTH_URL = "https://api.schwabapi.com/v1/oauth/authorize"
SCHWAB_TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"


def _basic_auth_header() -> str:
    creds = f"{settings.schwab_app_key}:{settings.schwab_app_secret}"
    return "Basic " + base64.b64encode(creds.encode()).decode()


def _callback_url(request: Request) -> str:
    """
    Build the callback URL.
    Uses SCHWAB_CALLBACK_URL from settings if it looks like a real URL,
    otherwise constructs from the current request base URL.
    """
    configured = settings.schwab_callback_url
    if configured and configured.startswith("http") and "127.0.0.1" not in configured:
        return configured
    # Fallback: derive from the incoming request
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/schwab/callback"


@router.get("/status")
async def schwab_status():
    """Return the current Schwab connection state."""
    from app.schwab.client import schwab_client
    return schwab_client.connection_status()


@router.get("/connect")
async def schwab_connect(request: Request):
    """Redirect the browser to Schwab's OAuth authorization page."""
    if settings.mock_schwab:
        return {"error": "Mock mode — OAuth not available"}

    callback = _callback_url(request)
    auth_url = (
        f"{SCHWAB_AUTH_URL}"
        f"?client_id={settings.schwab_app_key}"
        f"&redirect_uri={callback}"
        f"&response_type=code"
    )
    logger.info("Redirecting to Schwab OAuth", callback_url=callback)
    return RedirectResponse(auth_url)


@router.get("/callback")
async def schwab_callback(request: Request, code: str | None = None, error: str | None = None):
    """
    Schwab redirects here after the user authorizes the app.
    Exchange the code for tokens, save to DB + file, re-initialize client.
    """
    if error:
        logger.warning("Schwab OAuth error in callback", error=error)
        return RedirectResponse(f"/?schwab_error={error}")

    if not code:
        return RedirectResponse("/?schwab_error=missing_code")

    callback = _callback_url(request)

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SCHWAB_TOKEN_URL,
                headers={
                    "Authorization": _basic_auth_header(),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": callback,
                },
                timeout=15,
            )
            resp.raise_for_status()
            oauth_resp = resp.json()
    except Exception as exc:
        logger.error("Schwab token exchange failed", error=str(exc))
        return RedirectResponse(f"/?schwab_error=token_exchange_failed")

    # Build token dict in schwab-py format and persist
    from app.schwab.token_store import build_token_dict, save_token_to_db
    token_dict = build_token_dict(oauth_resp)
    await save_token_to_db(token_dict)

    # Also write to file so schwab-py can read it
    import json
    with open(settings.schwab_token_path, "w") as f:
        json.dump(token_dict, f)

    logger.info("Schwab token obtained and saved via OAuth callback")

    # Re-initialize the Schwab client
    from app.schwab.client import schwab_client
    await schwab_client.initialize()

    if schwab_client.is_connected:
        # Restart streaming if it was down
        try:
            from app.schwab.stream_manager import stream_manager
            await stream_manager.start()
        except Exception:
            pass

    return RedirectResponse("/?schwab_connected=1")


@router.post("/refresh")
async def schwab_refresh():
    """Force-refresh the Schwab access token using the stored refresh token."""
    if settings.mock_schwab:
        return {"success": True, "message": "Mock mode — no refresh needed"}

    import json
    import os

    # Load current token
    from app.schwab.token_store import load_token_from_db, save_token_to_db
    token_dict = await load_token_from_db()

    if not token_dict and os.path.exists(settings.schwab_token_path):
        with open(settings.schwab_token_path) as f:
            token_dict = json.load(f)

    if not token_dict:
        return {"success": False, "error": "No token stored — connect Schwab first"}

    inner = token_dict.get("token", token_dict)
    refresh_token = inner.get("refresh_token")
    if not refresh_token:
        return {"success": False, "error": "No refresh_token found in stored token"}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                SCHWAB_TOKEN_URL,
                headers={
                    "Authorization": _basic_auth_header(),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                },
                timeout=15,
            )
            resp.raise_for_status()
            oauth_resp = resp.json()
    except Exception as exc:
        logger.error("Schwab token refresh failed", error=str(exc))
        return {"success": False, "error": str(exc)}

    from app.schwab.token_store import build_token_dict
    new_token_dict = build_token_dict(oauth_resp)
    await save_token_to_db(new_token_dict)

    with open(settings.schwab_token_path, "w") as f:
        json.dump(new_token_dict, f)

    # Re-initialize client with fresh token
    from app.schwab.client import schwab_client
    await schwab_client.initialize()

    return {"success": schwab_client.is_connected, "status": schwab_client.connection_status()}


@router.post("/reconnect")
async def schwab_reconnect():
    """Re-attempt initialization from the existing token (DB or file)."""
    from app.schwab.client import schwab_client

    await schwab_client.initialize()

    if schwab_client.is_connected and not settings.mock_schwab:
        try:
            from app.schwab.stream_manager import stream_manager
            await stream_manager.start()
        except Exception:
            pass

    return {"success": schwab_client.is_connected, "status": schwab_client.connection_status()}
