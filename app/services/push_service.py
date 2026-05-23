"""
PWA Web Push notification service using VAPID keys.

Setup:
  1. Generate keys: npx web-push generate-vapid-keys
  2. Set VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY, VAPID_SUBJECT in .env
  3. Frontend subscribes via /api/push/subscribe
  4. Call push_service.send_push(title, body) to notify all subscribed devices
"""
import json
import asyncio
import structlog

logger = structlog.get_logger(__name__)


class PushService:
    async def send_push(self, title: str, body: str, url: str = "/") -> int:
        """
        Send a push notification to all subscribed devices.
        Returns number of successful deliveries.
        """
        from app.config import settings
        if not settings.vapid_private_key or not settings.vapid_public_key:
            logger.warning("Push not sent — VAPID keys not configured")
            return 0

        subscriptions = await self._get_subscriptions()
        if not subscriptions:
            return 0

        payload = json.dumps({"title": title, "body": body, "url": url})
        success = 0
        stale = []

        for sub in subscriptions:
            try:
                await asyncio.to_thread(self._send_one, sub, payload)
                success += 1
            except Exception as exc:
                err = str(exc)
                if "410" in err or "404" in err:
                    # Subscription expired — mark for removal
                    stale.append(sub["endpoint"])
                else:
                    logger.warning("Push delivery failed", error=err)

        if stale:
            await self._remove_stale(stale)

        logger.info("Push notifications sent", success=success, total=len(subscriptions))
        return success

    def _send_one(self, subscription: dict, payload: str) -> None:
        from pywebpush import webpush, WebPushException
        from app.config import settings
        webpush(
            subscription_info={
                "endpoint": subscription["endpoint"],
                "keys": subscription["keys"],
            },
            data=payload,
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
            content_encoding="aes128gcm",
        )

    async def _get_subscriptions(self) -> list[dict]:
        from sqlalchemy import select
        from app.database import AsyncSessionLocal
        from app.models.push_subscription import PushSubscription
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(PushSubscription))
            rows = result.scalars().all()
        return [{"endpoint": r.endpoint, "keys": r.keys} for r in rows]

    async def _remove_stale(self, endpoints: list[str]) -> None:
        from sqlalchemy import delete
        from app.database import AsyncSessionLocal
        from app.models.push_subscription import PushSubscription
        async with AsyncSessionLocal() as db:
            await db.execute(delete(PushSubscription).where(PushSubscription.endpoint.in_(endpoints)))
            await db.commit()
        logger.info("Removed stale push subscriptions", count=len(endpoints))

    async def save_subscription(self, endpoint: str, keys: dict) -> None:
        from datetime import datetime, timezone
        from sqlalchemy import select
        from app.database import AsyncSessionLocal
        from app.models.push_subscription import PushSubscription
        async with AsyncSessionLocal() as db:
            existing = await db.execute(select(PushSubscription).where(PushSubscription.endpoint == endpoint))
            if not existing.scalar_one_or_none():
                db.add(PushSubscription(endpoint=endpoint, keys=keys, created_at=datetime.now(timezone.utc)))
                await db.commit()
        logger.info("Push subscription saved")

    async def remove_subscription(self, endpoint: str) -> None:
        from sqlalchemy import delete
        from app.database import AsyncSessionLocal
        from app.models.push_subscription import PushSubscription
        async with AsyncSessionLocal() as db:
            await db.execute(delete(PushSubscription).where(PushSubscription.endpoint == endpoint))
            await db.commit()


push_service = PushService()
