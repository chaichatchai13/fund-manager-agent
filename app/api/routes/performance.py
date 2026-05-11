from datetime import date

from fastapi import APIRouter

from app.schemas.performance import ClosedTradeResponse, DailySnapshotResponse, PerformanceSummary

router = APIRouter(prefix="/api/performance", tags=["performance"])


@router.get("/summary", response_model=PerformanceSummary)
async def get_summary(period: str = "month"):
    from app.services.performance_tracker import performance_tracker
    return await performance_tracker.get_summary(period)


@router.get("/daily", response_model=list[DailySnapshotResponse])
async def get_daily(
    start_date: date = date(2024, 1, 1),
    end_date: date | None = None,
):
    from app.services.performance_tracker import performance_tracker
    if end_date is None:
        end_date = date.today()
    return await performance_tracker.get_daily_series(start_date, end_date)


@router.get("/trades", response_model=list[ClosedTradeResponse])
async def get_trades(symbol: str | None = None, limit: int = 50):
    from app.services.performance_tracker import performance_tracker
    return await performance_tracker.get_trade_history(symbol=symbol, limit=limit)
