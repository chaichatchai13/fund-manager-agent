"""
IV Rank tracker.

Schwab doesn't provide IV Rank natively. We approximate it using
52-week historical option IV data fetched via get_price_history_every_day().

IV Rank = (current IV - 52w low IV) / (52w high IV - 52w low IV) × 100

Since historical options IV isn't available via Schwab's price history (only OHLCV),
we use historical close-to-close volatility as a proxy and compute its rank.
The nightly job refreshes these values.
"""
import math
import statistics
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class IVRankTracker:
    """
    In-memory store of historical volatility rank per symbol.
    Populated at startup and refreshed nightly via refresh_symbol().
    """

    def __init__(self) -> None:
        # symbol -> {"iv_rank": float, "current_iv": float, "updated": date}
        self._data: dict[str, dict] = defaultdict(lambda: {"iv_rank": 50.0, "current_iv": 0.0, "updated": None})

    def get_iv_rank(self, symbol: str) -> float:
        return self._data[symbol]["iv_rank"]

    async def refresh_symbol(self, symbol: str, schwab_client: Any) -> None:
        try:
            raw = await schwab_client.get_price_history(symbol)
            candles = raw.get("candles", [])
            if len(candles) < 30:
                return

            closes = [c["close"] for c in candles if c.get("close")]
            hv_series = _compute_hv20_series(closes)

            if not hv_series:
                return

            current_hv = hv_series[-1]
            min_hv = min(hv_series)
            max_hv = max(hv_series)

            if max_hv - min_hv < 0.001:
                iv_rank = 50.0
            else:
                iv_rank = round((current_hv - min_hv) / (max_hv - min_hv) * 100, 1)

            self._data[symbol] = {
                "iv_rank": iv_rank,
                "current_iv": round(current_hv * 100, 1),
                "updated": date.today(),
            }
            logger.info("IV rank updated", symbol=symbol, iv_rank=iv_rank)
        except Exception as exc:
            logger.warning("Failed to compute IV rank", symbol=symbol, error=str(exc))

    async def refresh_all(self, symbols: list[str], schwab_client: Any) -> None:
        for symbol in symbols:
            await self.refresh_symbol(symbol, schwab_client)


def _compute_hv20_series(closes: list[float]) -> list[float]:
    """Compute 20-day rolling historical volatility (annualized) series."""
    if len(closes) < 21:
        return []
    log_returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    hv_series = []
    window = 20
    for i in range(window, len(log_returns) + 1):
        window_returns = log_returns[i - window:i]
        std = statistics.stdev(window_returns)
        hv_annualized = std * math.sqrt(252)
        hv_series.append(hv_annualized)
    return hv_series


# Singleton
iv_rank_tracker = IVRankTracker()
