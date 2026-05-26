"""
AI Provider abstraction — routes text generation to Claude, GPT, Gemini, or Grok.

Used for social post summarization. Agent chat always uses Claude (tool-use).

Provider IDs (stored in app_settings):
  claude  → claude-haiku-4-5         (Anthropic)
  gpt     → gpt-4o-mini              (OpenAI)
  gemini  → gemini-1.5-flash         (Google)
  grok    → grok-3-mini-fast         (xAI — OpenAI-compatible endpoint)
"""
import structlog
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.app_settings import AppSettings

logger = structlog.get_logger(__name__)

SETTINGS_KEY = "ai_model"

PROVIDER_LABELS = {
    "claude": "Claude (Haiku)",
    "gpt":    "GPT-4o Mini",
    "gemini": "Gemini 1.5 Flash",
    "grok":   "Grok 3 Mini",
}

VALID_PROVIDERS = list(PROVIDER_LABELS.keys())


async def get_active_model() -> str:
    """Return the currently configured AI provider ID."""
    from app.config import settings
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AppSettings).where(AppSettings.key == SETTINGS_KEY))
        row = result.scalar_one_or_none()
        if row and row.value in VALID_PROVIDERS:
            return row.value
    # Fall back to .env default
    return settings.default_ai_model or "claude"


async def set_active_model(provider: str) -> None:
    """Persist the chosen AI provider."""
    if provider not in VALID_PROVIDERS:
        raise ValueError(f"Unknown provider '{provider}'. Must be one of {VALID_PROVIDERS}")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AppSettings).where(AppSettings.key == SETTINGS_KEY))
        row = result.scalar_one_or_none()
        if row:
            row.value = provider
        else:
            db.add(AppSettings(key=SETTINGS_KEY, value=provider))
        await db.commit()


async def generate_text(prompt: str) -> str:
    """Route a text-generation call to whichever provider is active."""
    provider = await get_active_model()
    try:
        if provider == "claude":
            return await _claude(prompt)
        elif provider == "gpt":
            return await _gpt(prompt)
        elif provider == "gemini":
            return await _gemini(prompt)
        elif provider == "grok":
            return await _grok(prompt)
        else:
            return await _claude(prompt)  # safe default
    except Exception as exc:
        logger.error("AI provider call failed", provider=provider, error=str(exc))
        raise


# ── Provider implementations ──────────────────────────────────────────────────

async def _claude(prompt: str) -> str:
    import anthropic
    from app.config import settings
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


async def _gpt(prompt: str) -> str:
    from openai import AsyncOpenAI
    from app.config import settings
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY not configured")
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    resp = await client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""


async def _gemini(prompt: str) -> str:
    import httpx
    from app.config import settings
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY not configured")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={settings.gemini_api_key}"
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


async def _grok(prompt: str) -> str:
    from openai import AsyncOpenAI
    from app.config import settings
    if not settings.xai_api_key:
        raise RuntimeError("XAI_API_KEY not configured")
    client = AsyncOpenAI(api_key=settings.xai_api_key, base_url="https://api.x.ai/v1")
    resp = await client.chat.completions.create(
        model="grok-3-mini-fast",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.choices[0].message.content or ""
