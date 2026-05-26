"""AI model settings — read and update the active AI provider."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/ai", tags=["ai-settings"])


class SetModelRequest(BaseModel):
    provider: str   # "claude" | "gpt" | "gemini" | "grok"


@router.get("/model")
async def get_model():
    """Return active AI model plus which API keys are configured."""
    from app.services.ai_provider import get_active_model, PROVIDER_LABELS, VALID_PROVIDERS
    from app.config import settings

    active = await get_active_model()

    configured = {
        "claude": bool(settings.anthropic_api_key),
        "gpt":    bool(settings.openai_api_key),
        "gemini": bool(settings.gemini_api_key),
        "grok":   bool(settings.xai_api_key),
    }

    return {
        "active": active,
        "providers": [
            {
                "id": p,
                "label": PROVIDER_LABELS[p],
                "configured": configured.get(p, False),
            }
            for p in VALID_PROVIDERS
        ],
    }


@router.post("/model")
async def set_model(body: SetModelRequest):
    """Switch the active AI provider."""
    from app.services.ai_provider import set_active_model, VALID_PROVIDERS
    if body.provider not in VALID_PROVIDERS:
        raise HTTPException(status_code=400, detail=f"Unknown provider '{body.provider}'")
    await set_active_model(body.provider)
    return {"ok": True, "active": body.provider}
