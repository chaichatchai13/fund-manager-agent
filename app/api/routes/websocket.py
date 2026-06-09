"""
WebSocket endpoint for live dashboard updates.
Sends position price updates and new position events to connected clients.
"""
import asyncio
import json

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.position import OptionPosition

router = APIRouter(tags=["websocket"])
logger = structlog.get_logger(__name__)

# Track all connected WebSocket clients
_connected_clients: set[WebSocket] = set()


@router.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    # Accept the HTTP upgrade first, then verify auth.
    # Closing before accept() causes FastAPI to return 403 instead of our custom code.
    await websocket.accept()

    from app.auth.security import COOKIE_NAME, decode_token
    token = websocket.cookies.get(COOKIE_NAME)
    if not token or not decode_token(token):
        await websocket.close(code=4001)  # 4001 = Unauthorized
        return
    _connected_clients.add(websocket)
    logger.info("WebSocket client connected", total=len(_connected_clients))

    try:
        # Send initial state: all open positions
        await _send_initial_state(websocket)

        # Listen for stream updates and forward to this client
        from app.schwab.stream_manager import stream_manager
        while True:
            try:
                update = stream_manager.update_queue.get_nowait()
                await websocket.send_text(json.dumps(update))
                # If it's a price update, also send position P&L update
                if update.get("type") == "price_update":
                    await _send_position_update(websocket, update["symbol"], update["price"])
            except asyncio.QueueEmpty:
                # Send a heartbeat and check for client disconnect
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                except asyncio.TimeoutError:
                    pass
                await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("WebSocket error", error=str(exc))
    finally:
        _connected_clients.discard(websocket)
        logger.info("WebSocket client disconnected", total=len(_connected_clients))


async def broadcast(message: dict) -> None:
    """Broadcast a message to all connected WebSocket clients."""
    if not _connected_clients:
        return
    text = json.dumps(message, default=str)
    disconnected = set()
    for client in _connected_clients:
        try:
            await client.send_text(text)
        except Exception:
            disconnected.add(client)
    _connected_clients -= disconnected


def _position_to_dict(p: OptionPosition) -> dict:
    """Serialize a position to a dict matching the OptionPositionResponse schema."""
    return {
        "id": p.id,
        "rule_id": p.rule_id,
        "underlying_symbol": p.underlying_symbol,
        "option_symbol": p.option_symbol,
        "strike": p.strike,
        "expiration_date": str(p.expiration_date),
        "dte_at_entry": p.dte_at_entry,
        "delta_at_entry": p.delta_at_entry,
        "iv_rank_at_entry": p.iv_rank_at_entry,
        "stock_price_at_entry": p.stock_price_at_entry,
        "contracts": p.contracts,
        "premium_received": p.premium_received,
        "total_credit": p.total_credit,
        "current_price": p.current_price,
        "unrealized_pnl": p.unrealized_pnl,
        "status": p.status,
        "entry_order_id": p.entry_order_id,
        "exit_order_id": p.exit_order_id,
        "opened_at": p.opened_at.isoformat() if p.opened_at else None,
        "closed_at": p.closed_at.isoformat() if p.closed_at else None,
    }


async def broadcast_positions() -> None:
    """Fetch all active positions from DB and broadcast to all clients (used after reconciliation)."""
    if not _connected_clients:
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OptionPosition).where(OptionPosition.status.in_(["OPEN", "CLOSING"]))
        )
        positions = result.scalars().all()
    payload = {
        "type": "initial_state",
        "positions": [_position_to_dict(p) for p in positions],
    }
    await broadcast(payload)


async def _send_initial_state(websocket: WebSocket) -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OptionPosition).where(OptionPosition.status.in_(["OPEN", "CLOSING"]))
        )
        positions = result.scalars().all()

    payload = {
        "type": "initial_state",
        "positions": [_position_to_dict(p) for p in positions],
    }
    await websocket.send_text(json.dumps(payload, default=str))


async def _send_position_update(websocket: WebSocket, option_symbol: str, current_price: float) -> None:
    # Schwab stream may return symbols with spaces; DB stores with underscores — normalise both ways
    normalised = option_symbol.replace(" ", "_").upper()
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OptionPosition).where(
                OptionPosition.option_symbol.in_([option_symbol, normalised]),
                OptionPosition.status.in_(["OPEN", "CLOSING"]),
            )
        )
        position = result.scalar_one_or_none()

    if not position:
        return

    unrealized_pnl = round((position.premium_received - current_price) * 100 * position.contracts, 2)
    pnl_pct = round((position.premium_received - current_price) / position.premium_received * 100, 1) if position.premium_received > 0 else 0

    await websocket.send_text(json.dumps({
        "type": "position_update",
        "position_id": position.id,
        "option_symbol": option_symbol,
        "current_price": current_price,
        "unrealized_pnl": unrealized_pnl,
        "pnl_pct": pnl_pct,
    }))
