"""
Social Intel service — fetches X (Twitter) posts via SocialData.tools API.

Filters posts by watched accounts × tracked stocks.
Caches posts in DB to support "since last check" and article rendering.
Generates AI summaries via Claude.

SocialData.tools API docs: https://socialdata.tools/docs
Usage-based pricing: ~$0.00016/tweet → ~$1-3/month for personal use.
"""
from datetime import datetime, timezone
from typing import Optional

import httpx
import structlog
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.social_watchlist import SocialLastChecked, SocialPost, SocialWatchlist

logger = structlog.get_logger(__name__)

SOCIALDATA_BASE = "https://api.socialdata.tools"


class SocialService:

    def _headers(self) -> dict:
        from app.config import settings
        if not settings.socialdata_api_key:
            raise RuntimeError("SOCIALDATA_API_KEY not configured — sign up at https://socialdata.tools to enable X.com post summaries")
        return {
            "Authorization": f"Bearer {settings.socialdata_api_key}",
            "Accept": "application/json",
        }

    def _api_configured(self) -> bool:
        from app.config import settings
        return bool(settings.socialdata_api_key)

    # ── Watchlist management ────────────────────────────────────────────────

    async def get_watchlist(self) -> list[dict]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SocialWatchlist))
            rows = result.scalars().all()
        return [{"id": r.id, "x_handle": r.x_handle, "display_name": r.display_name, "stocks": r.stocks} for r in rows]

    async def add_to_watchlist(self, x_handle: str, stocks: list[str]) -> dict:
        handle = x_handle.lstrip("@").lower()
        stocks = [s.upper() for s in stocks]

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(SocialWatchlist).where(SocialWatchlist.x_handle == handle))
            row = result.scalar_one_or_none()
            if row:
                # Merge stocks
                existing = set(row.stocks or [])
                row.stocks = list(existing | set(stocks))
            else:
                row = SocialWatchlist(x_handle=handle, stocks=stocks, added_at=datetime.now(timezone.utc))
                db.add(row)
            await db.commit()

        return {"ok": True, "x_handle": handle, "stocks": stocks}

    async def remove_from_watchlist(self, x_handle: str) -> dict:
        from sqlalchemy import delete
        handle = x_handle.lstrip("@").lower()
        async with AsyncSessionLocal() as db:
            await db.execute(delete(SocialWatchlist).where(SocialWatchlist.x_handle == handle))
            await db.commit()
        return {"ok": True, "removed": handle}

    # ── Post fetching ────────────────────────────────────────────────────────

    async def fetch_posts_for_handle(self, x_handle: str, stocks: list[str], since: Optional[datetime] = None) -> list[dict]:
        """Fetch posts from an X account mentioning specific stock tickers."""
        posts = []
        for stock in stocks:
            query = f"from:{x_handle} ${stock}"
            fetched = await self._search_tweets(query, since=since)
            for tweet in fetched:
                posts.append({**tweet, "stock": stock, "x_handle": x_handle})
        return posts

    async def _search_tweets(self, query: str, since: Optional[datetime] = None, limit: int = 20) -> list[dict]:
        """Search tweets via SocialData.tools."""
        try:
            params = {"query": query, "type": "Latest"}
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{SOCIALDATA_BASE}/twitter/search",
                    headers=self._headers(),
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()

            tweets = []
            for tweet in (data.get("tweets") or [])[:limit]:
                created_str = tweet.get("tweet_created_at", "")
                try:
                    created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                except Exception:
                    created_at = datetime.now(timezone.utc)

                if since and created_at <= since:
                    continue

                # Fetch referenced tweet (one level)
                referenced_id = None
                referenced_content = None
                if tweet.get("quoted_tweet"):
                    qt = tweet["quoted_tweet"]
                    referenced_id = str(qt.get("id_str", ""))
                    referenced_content = qt.get("full_text", "")
                elif tweet.get("in_reply_to_tweet_id"):
                    referenced_id = str(tweet["in_reply_to_tweet_id"])
                    referenced_content = await self._fetch_single_tweet(referenced_id)

                tweets.append({
                    "post_id": str(tweet.get("id_str", "")),
                    "content": tweet.get("full_text", ""),
                    "posted_at": created_at.isoformat(),
                    "image_urls": self._extract_images(tweet),
                    "referenced_post_id": referenced_id,
                    "referenced_content": referenced_content,
                })

            return tweets

        except RuntimeError:
            raise
        except Exception as exc:
            logger.error("Tweet search failed", query=query, error=str(exc))
            return []

    async def _fetch_single_tweet(self, tweet_id: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{SOCIALDATA_BASE}/twitter/statuses/show",
                    headers=self._headers(),
                    params={"id": tweet_id},
                )
                if resp.status_code == 200:
                    return resp.json().get("full_text")
        except Exception:
            pass
        return None

    def _extract_images(self, tweet: dict) -> list[str]:
        urls = []
        media = tweet.get("entities", {}).get("media", [])
        for m in media:
            if m.get("type") == "photo":
                urls.append(m.get("media_url_https", ""))
        return [u for u in urls if u]

    # ── Summary with AI ──────────────────────────────────────────────────────

    async def get_summary(self, stocks: list[str] = None, since_last_check: bool = True, language: str = "English") -> dict:
        """
        Fetch and summarize posts for all watched accounts × stocks.
        Returns structured data suitable for the article-style UI.
        """
        if not self._api_configured():
            return {"posts": [], "message": "SOCIALDATA_API_KEY not configured. Sign up at https://socialdata.tools to enable X.com post summaries."}

        watchlist = await self.get_watchlist()
        if not watchlist:
            return {"posts": [], "message": "No accounts in watchlist. Add some with add_social_watchlist."}

        all_posts = []
        for entry in watchlist:
            handle = entry["x_handle"]
            tracked_stocks = stocks if stocks else entry["stocks"]
            if not tracked_stocks:
                continue

            since = await self._get_last_checked(handle, tracked_stocks[0]) if since_last_check else None
            posts = await self.fetch_posts_for_handle(handle, tracked_stocks, since=since)
            all_posts.extend(posts)

        if not all_posts:
            return {"posts": [], "message": "No new posts since last check."}

        # Generate AI summaries
        summarized = await self._summarize_posts(all_posts, language=language)

        # Save to DB + update last_checked
        await self._save_posts(summarized)
        await self._update_last_checked(watchlist, stocks)

        return {"posts": summarized, "count": len(summarized)}

    async def resummary_posts(self, post_ids: list[str] | None = None, language: str = "English") -> dict:
        """Re-summarize existing cached posts in a given language and update the DB."""
        from sqlalchemy import desc
        async with AsyncSessionLocal() as db:
            q = select(SocialPost).order_by(desc(SocialPost.posted_at)).limit(100)
            if post_ids:
                q = q.where(SocialPost.post_id.in_(post_ids))
            result = await db.execute(q)
            rows = result.scalars().all()

        if not rows:
            return {"updated": 0}

        post_dicts = [
            {
                "post_id": r.post_id,
                "x_handle": r.x_handle,
                "stock": r.stock,
                "content": r.content,
                "referenced_content": r.referenced_content,
            }
            for r in rows
        ]

        summarized = await self._summarize_posts(post_dicts, language=language)
        summary_map = {p["post_id"]: p["summary"] for p in summarized}

        async with AsyncSessionLocal() as db:
            for row_id, post_id in [(r.id, r.post_id) for r in rows]:
                result = await db.execute(select(SocialPost).where(SocialPost.id == row_id))
                row = result.scalar_one_or_none()
                if row and post_id in summary_map:
                    row.summary = summary_map[post_id]
            await db.commit()

        return {"updated": len(summarized), "language": language}

    async def _summarize_posts(self, posts: list[dict], language: str = "English") -> list[dict]:
        """Generate a one-paragraph summary for each post using Claude."""
        import anthropic
        from app.config import settings
        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

        lang_instruction = "" if language == "English" else f" Write the summary in {language}."

        result = []
        for post in posts:
            try:
                prompt = (
                    f"Summarize this X post about ${post['stock']} from @{post['x_handle']} "
                    f"in 1-2 sentences for a trader. Focus on actionable insight.{lang_instruction}\n\n"
                    f"Post: {post['content']}\n"
                )
                if post.get("referenced_content"):
                    prompt += f"Referenced post: {post['referenced_content']}\n"

                resp = await client.messages.create(
                    model="claude-haiku-4-5",
                    max_tokens=300,
                    messages=[{"role": "user", "content": prompt}],
                )
                summary = resp.content[0].text if resp.content else post["content"][:200]
            except Exception:
                summary = post["content"][:300]

            result.append({**post, "summary": summary})

        return result

    async def _save_posts(self, posts: list[dict]) -> None:
        async with AsyncSessionLocal() as db:
            for post in posts:
                result = await db.execute(select(SocialPost).where(SocialPost.post_id == post["post_id"]))
                if result.scalar_one_or_none():
                    continue  # already cached
                try:
                    posted_at = datetime.fromisoformat(post["posted_at"])
                except Exception:
                    posted_at = datetime.now(timezone.utc)

                db.add(SocialPost(
                    post_id=post["post_id"],
                    x_handle=post["x_handle"],
                    stock=post["stock"],
                    content=post["content"],
                    summary=post.get("summary"),
                    image_urls=post.get("image_urls"),
                    referenced_post_id=post.get("referenced_post_id"),
                    referenced_content=post.get("referenced_content"),
                    posted_at=posted_at,
                    fetched_at=datetime.now(timezone.utc),
                ))
            await db.commit()

    async def _get_last_checked(self, handle: str, stock: str) -> Optional[datetime]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(SocialLastChecked).where(
                    SocialLastChecked.x_handle == handle,
                    SocialLastChecked.stock == stock,
                )
            )
            row = result.scalar_one_or_none()
        return row.last_checked_at if row else None

    async def _update_last_checked(self, watchlist: list[dict], stocks: Optional[list[str]]) -> None:
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            for entry in watchlist:
                handle = entry["x_handle"]
                tracked = stocks if stocks else entry["stocks"]
                for stock in tracked:
                    result = await db.execute(
                        select(SocialLastChecked).where(
                            SocialLastChecked.x_handle == handle,
                            SocialLastChecked.stock == stock,
                        )
                    )
                    row = result.scalar_one_or_none()
                    if row:
                        row.last_checked_at = now
                    else:
                        db.add(SocialLastChecked(x_handle=handle, stock=stock, last_checked_at=now))
            await db.commit()

    async def get_cached_posts(self, stock: Optional[str] = None, x_handle: Optional[str] = None, limit: int = 50) -> list[dict]:
        """Return cached posts from DB for the UI feed."""
        from sqlalchemy import desc
        async with AsyncSessionLocal() as db:
            q = select(SocialPost).order_by(desc(SocialPost.posted_at)).limit(limit)
            if stock:
                q = q.where(SocialPost.stock == stock.upper())
            if x_handle:
                q = q.where(SocialPost.x_handle == x_handle.lstrip("@").lower())
            result = await db.execute(q)
            posts = result.scalars().all()

        return [
            {
                "id": p.id,
                "post_id": p.post_id,
                "x_handle": p.x_handle,
                "stock": p.stock,
                "content": p.content,
                "summary": p.summary,
                "image_urls": p.image_urls or [],
                "referenced_post_id": p.referenced_post_id,
                "referenced_content": p.referenced_content,
                "posted_at": p.posted_at.isoformat() if p.posted_at else None,
            }
            for p in posts
        ]


social_service = SocialService()
