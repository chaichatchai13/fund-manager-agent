"""
Research service — web search and news via Brave Search API.

Free tier: 2,000 queries/month
Docs: https://api.search.brave.com/app/documentation
"""
import structlog
import httpx

logger = structlog.get_logger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
BRAVE_NEWS_URL = "https://api.search.brave.com/res/v1/news/search"


class ResearchService:

    def _headers(self) -> dict:
        from app.config import settings
        if not settings.brave_api_key:
            raise RuntimeError("BRAVE_API_KEY not configured")
        return {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": settings.brave_api_key,
        }

    async def search(self, query: str, count: int = 5) -> dict:
        """General web search."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    BRAVE_SEARCH_URL,
                    headers=self._headers(),
                    params={"q": query, "count": min(count, 10), "safesearch": "off"},
                )
                resp.raise_for_status()
                data = resp.json()

            results = []
            for item in data.get("web", {}).get("results", []):
                results.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "description": item.get("description"),
                    "published": item.get("page_age"),
                })
            return {"query": query, "results": results}

        except Exception as exc:
            logger.error("Web search failed", query=query, error=str(exc))
            return {"query": query, "results": [], "error": str(exc)}

    async def search_news(self, symbol: str, days_back: int = 7) -> dict:
        """Search for recent news about a stock ticker."""
        query = f"${symbol} stock news"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    BRAVE_NEWS_URL,
                    headers=self._headers(),
                    params={"q": query, "count": 10, "freshness": f"p{days_back}d"},
                )
                resp.raise_for_status()
                data = resp.json()

            articles = []
            for item in data.get("results", []):
                articles.append({
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "description": item.get("description"),
                    "source": item.get("meta_url", {}).get("hostname"),
                    "published": item.get("age"),
                    "thumbnail": item.get("thumbnail", {}).get("src"),
                })
            return {"symbol": symbol, "days_back": days_back, "articles": articles}

        except Exception as exc:
            logger.error("News search failed", symbol=symbol, error=str(exc))
            return {"symbol": symbol, "articles": [], "error": str(exc)}

    async def search_analyst_targets(self, symbol: str) -> dict:
        """Search for analyst price targets for a stock."""
        return await self.search(f"{symbol} stock analyst price target rating 2026", count=5)

    async def search_earnings(self, symbol: str) -> dict:
        """Search for upcoming or recent earnings info."""
        return await self.search(f"{symbol} earnings date EPS revenue 2026", count=5)


research_service = ResearchService()
