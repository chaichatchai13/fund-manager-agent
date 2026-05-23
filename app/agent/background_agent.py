"""
Background Agent — runs on a schedule without user interaction.

Jobs:
  - morning_digest()     : 8 AM ET — fetch social posts + news, send SMS + push summary
  - evening_prep()       : 5 PM ET — research prep for next day's scan targets
  - alert_open_prices()  : 9:30 AM ET — load open prices for alert % calculations
"""
import structlog

logger = structlog.get_logger(__name__)


async def morning_digest() -> None:
    """
    Fetch new social posts + top news for all watched stocks.
    Summarize via Claude and send as SMS + push notification.
    """
    logger.info("Background agent: morning digest starting")
    try:
        from app.services.social_service import social_service
        from app.services.research_service import research_service
        from app.services.sms_service import sms_service
        from app.services.push_service import push_service

        # Get social summary
        summary = await social_service.get_summary(since_last_check=True)
        posts = summary.get("posts", [])

        # Get top news for each watched stock
        watchlist = await social_service.get_watchlist()
        all_stocks = set()
        for entry in watchlist:
            all_stocks.update(entry.get("stocks", []))

        news_summaries = []
        for stock in list(all_stocks)[:5]:  # limit to 5 stocks
            news = await research_service.search_news(stock, days_back=1)
            articles = news.get("articles", [])
            if articles:
                news_summaries.append(f"${stock}: {articles[0]['title']}")

        # Build digest message
        lines = ["📊 ThetaFlow Morning Digest\n"]

        if posts:
            lines.append(f"🐦 {len(posts)} new X posts on your watchlist:")
            for p in posts[:3]:
                lines.append(f"  @{p['x_handle']} on ${p['stock']}: {p['summary'][:100]}")
        else:
            lines.append("🐦 No new X posts since last check.")

        if news_summaries:
            lines.append(f"\n📰 Top news:")
            lines.extend([f"  {n}" for n in news_summaries[:3]])

        lines.append("\nOpen ThetaFlow for full details.")
        message = "\n".join(lines)

        await sms_service.send_sms(message)
        await push_service.send_push(
            "ThetaFlow Morning Digest",
            f"{len(posts)} new posts · {len(news_summaries)} news items",
            url="/?tab=social",
        )

        logger.info("Morning digest sent", posts=len(posts), news=len(news_summaries))

    except Exception as exc:
        logger.error("Morning digest failed", error=str(exc))


async def alert_open_prices() -> None:
    """Load today's open prices for all alert symbols at market open (9:30 AM ET)."""
    logger.info("Background agent: loading open prices for alerts")
    try:
        from app.services.alert_service import alert_service
        symbols = await alert_service.get_alert_symbols()
        if symbols:
            await alert_service.get_open_prices_from_schwab(symbols)
    except Exception as exc:
        logger.error("Open price load failed", error=str(exc))


async def evening_prep() -> None:
    """
    5 PM — Refresh IV ranks for all rule symbols so data is ready for next morning.
    Already handled by iv_refresh_job in scheduler, but we can add extra research here.
    """
    logger.info("Background agent: evening prep")
    try:
        # IV refresh is already handled by the existing iv_refresh_job
        # Future: add overnight earnings/news research here
        pass
    except Exception as exc:
        logger.error("Evening prep failed", error=str(exc))
