"""Social Intel API — watchlist management and post feed."""
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/social", tags=["social"])


class WatchlistAdd(BaseModel):
    x_handle: str
    stocks: list[str]


class RefreshRequest(BaseModel):
    stocks: list[str] | None = None
    language: str = "English"


class ResummaryRequest(BaseModel):
    post_ids: list[str] | None = None   # None = all cached posts
    language: str = "English"


@router.get("/config")
async def get_config():
    """Return server-side social intel configuration (e.g. default language)."""
    from app.config import settings
    return {"default_language": settings.social_summary_language or "English"}


@router.get("/watchlist")
async def get_watchlist():
    from app.services.social_service import social_service
    return await social_service.get_watchlist()


@router.post("/watchlist")
async def add_watchlist(body: WatchlistAdd):
    from app.services.social_service import social_service
    return await social_service.add_to_watchlist(body.x_handle, body.stocks)


@router.delete("/watchlist/{x_handle}")
async def remove_watchlist(x_handle: str):
    from app.services.social_service import social_service
    return await social_service.remove_from_watchlist(x_handle)


@router.get("/feed")
async def get_feed(stock: str | None = None, x_handle: str | None = None, limit: int = 50):
    """Return cached posts for the article-style UI feed."""
    from app.services.social_service import social_service
    return await social_service.get_cached_posts(stock=stock, x_handle=x_handle, limit=limit)


@router.post("/refresh")
async def refresh_feed(body: RefreshRequest | None = None):
    """Fetch new posts since last check and return summary."""
    from app.services.social_service import social_service
    stocks = body.stocks if body else None
    language = body.language if body else "English"
    return await social_service.get_summary(stocks=stocks, since_last_check=True, language=language)


@router.post("/resummary")
async def resummary(body: ResummaryRequest):
    """Re-summarize existing cached posts in a different language."""
    from app.services.social_service import social_service
    return await social_service.resummary_posts(post_ids=body.post_ids, language=body.language)
