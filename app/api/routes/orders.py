from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.order import Order
from app.schemas.order import OrderResponse

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.get("", response_model=list[OrderResponse])
async def list_orders(status: str | None = None, limit: int = 50, db: AsyncSession = Depends(get_db)):
    query = select(Order).order_by(Order.created_at.desc()).limit(limit)
    if status:
        query = query.where(Order.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/live")
async def list_live_orders():
    """
    Fetch all open orders directly from Schwab — includes orders placed
    outside ThetaFlow (via Schwab app, thinkorswim, Swagger, etc.).
    """
    from app.schwab.client import schwab_client
    if not schwab_client.is_connected:
        return []
    try:
        orders = await schwab_client.get_live_orders()
        # Return only working/queued orders for the UI
        active_statuses = {"WORKING", "QUEUED", "PENDING_ACTIVATION",
                           "AWAITING_PARENT_ORDER", "AWAITING_CONDITION",
                           "AWAITING_MANUAL_REVIEW", "ACCEPTED"}
        return [o for o in orders if o.get("status") in active_statuses]
    except Exception:
        return []


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, db: AsyncSession = Depends(get_db)):
    from fastapi import HTTPException
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
