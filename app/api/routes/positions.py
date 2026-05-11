from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.position import OptionPosition
from app.schemas.position import OptionPositionResponse

router = APIRouter(prefix="/api/positions", tags=["positions"])


@router.get("", response_model=list[OptionPositionResponse])
async def list_positions(status: str = "OPEN", db: AsyncSession = Depends(get_db)):
    query = select(OptionPosition).order_by(OptionPosition.opened_at.desc())
    if status != "ALL":
        query = query.where(OptionPosition.status == status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{position_id}", response_model=OptionPositionResponse)
async def get_position(position_id: str, db: AsyncSession = Depends(get_db)):
    position = await db.get(OptionPosition, position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    return position


class ClosePositionRequest(BaseModel):
    limit_price: float | None = None


@router.post("/reconcile")
async def reconcile_positions():
    """Manually trigger a Schwab reconciliation — syncs DB to match live account."""
    from app.services.position_reconciler import position_reconciler
    summary = await position_reconciler.reconcile()
    return summary


@router.delete("/{position_id}", status_code=204)
async def delete_position(position_id: str, db: AsyncSession = Depends(get_db)):
    """Hard-delete a phantom / ghost position that was never actually filled in the broker."""
    position = await db.get(OptionPosition, position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    await db.delete(position)
    await db.commit()


@router.post("/{position_id}/roll")
async def roll_position(position_id: str):
    """Manually trigger a roll for a specific position (BTC current + STO new OTM)."""
    from app.services.roll_manager import roll_manager
    try:
        new_position_id = await roll_manager.roll_position(position_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not new_position_id:
        raise HTTPException(status_code=422, detail="Roll could not be executed — no suitable OTM candidate found or order rejected")
    return {"message": "Roll executed", "new_position_id": new_position_id}


@router.post("/{position_id}/close")
async def close_position(
    position_id: str, body: ClosePositionRequest, db: AsyncSession = Depends(get_db)
):
    position = await db.get(OptionPosition, position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    if position.status not in ("OPEN", "CLOSING"):
        raise HTTPException(status_code=400, detail=f"Cannot close position with status {position.status}")

    limit_price = body.limit_price or position.current_price or round(position.premium_received * 0.25, 2)

    from app.services.order_manager import order_manager
    from app.services.position_manager import position_manager
    order = await order_manager.place_buy_to_close(
        option_symbol=position.option_symbol,
        quantity=position.contracts,
        limit_price=round(float(limit_price), 2),
        position_id=position_id,
    )
    await position_manager.mark_closing(position_id, order.id)
    return {"message": f"BTC order placed at ${limit_price}", "order_id": order.id}
