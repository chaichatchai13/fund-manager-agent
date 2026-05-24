"""
Auth middleware — protects all /api/* and /ws/* routes.

Public paths (no token required):
  /health          — Docker healthcheck
  /auth/*          — login / logout endpoints themselves
  /api/schwab/status — shown on login page so user knows connection state
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.auth.security import COOKIE_NAME, decode_token

# Routes that bypass auth entirely
_PUBLIC = (
    "/health",
    "/auth/",
    "/privacy",   # Privacy policy — required for Twilio 10DLC registration
    "/terms",     # Terms of service — required for Twilio 10DLC registration
    "/api/schwab/status",
    "/api/schwab/callback",  # Schwab OAuth redirect — no cookie yet
    "/api/schwab/connect",   # Initiates OAuth — user may not have cookie in new tab
    "/webhooks/",            # Twilio inbound SMS — no cookie, server-to-server
    "/api/push/vapid-public-key",  # Needed before login to set up push subscription
)

# Route prefixes that require a valid token
_PROTECTED = ("/api/", "/ws/")


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # WebSocket upgrades: pass through — auth is checked inside the WS handler
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        needs_auth = any(path.startswith(p) for p in _PROTECTED)
        is_public = any(path.startswith(p) for p in _PUBLIC)

        if needs_auth and not is_public:
            token = request.cookies.get(COOKIE_NAME)
            if not token or not decode_token(token):
                return JSONResponse(
                    {"detail": "Not authenticated"},
                    status_code=401,
                )

        return await call_next(request)
