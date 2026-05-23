"""
Price alert service — monitors live prices and triggers SMS + push when conditions are met.

Hooks into stream_manager's price_cache on every price update.
Respects cooldown_minutes to avoid alert spam.
"""
from datetime import datetime, timezone, timedelta

import structlog
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.alert import PriceAlert

logger = structlog.get_logger(__name__)

# Track open prices for % change calculation
# Populated from Schwab quotes at market open
_open_prices: dict[str, float] = {}


class AlertService:

    async def check_price(self, symbol: str, current_price: float) -> None:
        """
        Called on every price update from the stream.
        Checks all enabled alerts for this symbol and fires if conditions are met.
        """
        open_price = _open_prices.get(symbol)

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(PriceAlert).where(
                    PriceAlert.symbol == symbol,
                    PriceAlert.enabled == True,
                )
            )
            alerts = result.scalars().all()

        for alert in alerts:
            if not self._should_fire(alert):
                continue

            triggered = False
            message = ""

            if alert.condition == "drop_pct" and open_price and open_price > 0:
                change_pct = (current_price - open_price) / open_price * 100
                if change_pct <= -alert.threshold:
                    triggered = True
                    message = (
                        f"⚠️ {symbol} is down {abs(change_pct):.1f}% "
                        f"(${current_price:.2f} from open ${open_price:.2f}).\n"
                        f"Open sell put? Reply YES to execute or NO to dismiss."
                    )

            elif alert.condition == "rise_pct" and open_price and open_price > 0:
                change_pct = (current_price - open_price) / open_price * 100
                if change_pct >= alert.threshold:
                    triggered = True
                    message = (
                        f"📈 {symbol} is up {change_pct:.1f}% "
                        f"(${current_price:.2f} from open ${open_price:.2f})."
                    )

            elif alert.condition == "below_price" and current_price <= alert.threshold:
                triggered = True
                message = f"⬇️ {symbol} is below ${alert.threshold:.2f} (now ${current_price:.2f})."

            elif alert.condition == "above_price" and current_price >= alert.threshold:
                triggered = True
                message = f"⬆️ {symbol} is above ${alert.threshold:.2f} (now ${current_price:.2f})."

            if triggered:
                await self._fire_alert(alert, message, symbol, current_price)

    def _should_fire(self, alert: PriceAlert) -> bool:
        """Return True if alert is past its cooldown period."""
        if alert.last_triggered_at is None:
            return True
        elapsed = (datetime.now(timezone.utc) - alert.last_triggered_at).total_seconds() / 60
        return elapsed >= alert.cooldown_minutes

    async def _fire_alert(self, alert: PriceAlert, message: str, symbol: str, price: float) -> None:
        logger.info("Alert fired", symbol=symbol, condition=alert.condition, threshold=alert.threshold)

        # Update last_triggered_at
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(PriceAlert).where(PriceAlert.id == alert.id))
            row = result.scalar_one_or_none()
            if row:
                row.last_triggered_at = datetime.now(timezone.utc)
                await db.commit()

        # Send SMS
        from app.services.sms_service import sms_service
        await sms_service.send_sms(message)

        # Set pending confirmation if action requires YES/NO
        if alert.action == "notify_and_suggest" and "Reply YES" in message:
            from app.config import settings
            sms_service.set_pending_confirmation(
                settings.alert_phone_number,
                {"type": "open_sell_put", "symbol": symbol, "price": price, "alert_id": alert.id},
            )

        # Send push notification (shorter message for push)
        from app.services.push_service import push_service
        push_title = f"ThetaFlow Alert: {symbol}"
        push_body = message.split("\n")[0]  # first line only
        await push_service.send_push(push_title, push_body, url="/?tab=dashboard")

    def set_open_price(self, symbol: str, open_price: float) -> None:
        _open_prices[symbol] = open_price

    async def get_open_prices_from_schwab(self, symbols: list[str]) -> None:
        """Fetch open prices at market open for all symbols with active alerts."""
        try:
            from app.schwab.client import schwab_client
            quotes = await schwab_client.get_quotes(symbols)
            for symbol, data in quotes.items():
                open_p = data.get("quote", {}).get("openPrice")
                if open_p:
                    _open_prices[symbol] = open_p
            logger.info("Open prices loaded", count=len(_open_prices))
        except Exception as exc:
            logger.warning("Failed to load open prices", error=str(exc))

    async def get_alert_symbols(self) -> list[str]:
        """Return all symbols that have active alerts."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(PriceAlert.symbol).where(PriceAlert.enabled == True).distinct()
            )
            return [row[0] for row in result.fetchall()]


alert_service = AlertService()
