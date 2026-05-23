"""PWA push notification subscription management."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(prefix="/api/push", tags=["push"])


class PushSubscribeBody(BaseModel):
    endpoint: str
    keys: dict   # {"p256dh": "...", "auth": "..."}


@router.get("/vapid-public-key")
async def get_vapid_key():
    """Return the VAPID public key — needed by the frontend to subscribe."""
    return {"vapid_public_key": settings.vapid_public_key or ""}


@router.post("/subscribe")
async def subscribe(body: PushSubscribeBody):
    from app.services.push_service import push_service
    await push_service.save_subscription(body.endpoint, body.keys)
    return {"ok": True}


@router.post("/unsubscribe")
async def unsubscribe(body: PushSubscribeBody):
    from app.services.push_service import push_service
    await push_service.remove_subscription(body.endpoint)
    return {"ok": True}


@router.post("/test")
async def send_test_push():
    """Send a test push notification to all subscribed devices."""
    from app.services.push_service import push_service
    count = await push_service.send_push(
        "ThetaFlow Test",
        "Push notifications are working! ✅",
        url="/",
    )
    return {"delivered": count}
