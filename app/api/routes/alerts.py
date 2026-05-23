"""Alert management endpoints."""
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.alert import PriceAlert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


class AlertCreate(BaseModel):
    symbol: str
    condition: str          # "drop_pct" | "rise_pct" | "below_price" | "above_price"
    threshold: float
    action: str = "notify_and_suggest"
    cooldown_minutes: int = 60


@router.get("")
async def list_alerts():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(PriceAlert).order_by(PriceAlert.symbol))
        rows = result.scalars().all()
    return [
        {
            "id": r.id, "symbol": r.symbol, "condition": r.condition,
            "threshold": r.threshold, "action": r.action, "enabled": r.enabled,
            "cooldown_minutes": r.cooldown_minutes,
            "last_triggered_at": r.last_triggered_at.isoformat() if r.last_triggered_at else None,
        }
        for r in rows
    ]


@router.post("")
async def create_alert(body: AlertCreate):
    async with AsyncSessionLocal() as db:
        alert = PriceAlert(
            symbol=body.symbol.upper(),
            condition=body.condition,
            threshold=body.threshold,
            action=body.action,
            cooldown_minutes=body.cooldown_minutes,
            created_at=datetime.now(timezone.utc),
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)
    return {"id": alert.id, "symbol": alert.symbol, "condition": alert.condition}


@router.patch("/{alert_id}/toggle")
async def toggle_alert(alert_id: int):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(PriceAlert).where(PriceAlert.id == alert_id))
        alert = result.scalar_one_or_none()
        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")
        alert.enabled = not alert.enabled
        await db.commit()
    return {"id": alert_id, "enabled": alert.enabled}


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int):
    from sqlalchemy import delete as sql_delete
    async with AsyncSessionLocal() as db:
        await db.execute(sql_delete(PriceAlert).where(PriceAlert.id == alert_id))
        await db.commit()
    return {"ok": True}
