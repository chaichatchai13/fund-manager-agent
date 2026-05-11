"""
SchwabClient: a singleton wrapper around schwab-py that handles:
- Lazy initialization (OAuth2 on first use)
- Rate limiting (120 req/min max)
- Account hash retrieval
- High-level operations used by services
"""
import asyncio
from datetime import date
from typing import Any

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)

# Token bucket: 120 requests per 60 seconds
_RATE_LIMIT_REQUESTS = 110  # conservative
_RATE_LIMIT_PERIOD = 60.0


class _RateLimiter:
    def __init__(self, max_calls: int, period: float) -> None:
        self._max_calls = max_calls
        self._period = period
        self._semaphore = asyncio.Semaphore(max_calls)
        self._call_times: list[float] = []

    async def acquire(self) -> None:
        await self._semaphore.acquire()
        now = asyncio.get_event_loop().time()
        self._call_times = [t for t in self._call_times if now - t < self._period]
        if self._call_times:
            sleep_time = self._period - (now - self._call_times[0])
            if sleep_time > 0 and len(self._call_times) >= self._max_calls:
                await asyncio.sleep(sleep_time)
        self._call_times.append(asyncio.get_event_loop().time())
        self._semaphore.release()


class SchwabClient:
    def __init__(self) -> None:
        self._client = None
        self._account_hash: str | None = None
        self._rate_limiter = _RateLimiter(_RATE_LIMIT_REQUESTS, _RATE_LIMIT_PERIOD)

    async def initialize(self) -> None:
        if settings.mock_schwab:
            logger.info("Mock Schwab mode — skipping real authentication")
            self._account_hash = "MOCK_ACCOUNT_HASH"
            return

        import os
        import schwab

        token_path = settings.schwab_token_path
        if not os.path.exists(token_path):
            raise RuntimeError(
                f"Schwab token file not found at '{token_path}'.\n"
                "Run the one-time auth setup first:\n\n"
                "    poetry run python setup_schwab_auth.py\n"
            )

        # Load from saved token file — no browser interaction needed
        self._client = await asyncio.to_thread(
            schwab.auth.client_from_token_file,
            token_path,
            settings.schwab_app_key,
            settings.schwab_app_secret,
        )

        # Fetch account hash
        response = await asyncio.to_thread(self._client.get_account_numbers)
        accounts = response.json()
        self._account_hash = accounts[0]["hashValue"]
        logger.info("Schwab client initialized", account_hash=self._account_hash[:8] + "***")

    @property
    def account_hash(self) -> str:
        if not self._account_hash:
            raise RuntimeError("SchwabClient not initialized — call initialize() first")
        return self._account_hash

    async def get_quotes(self, symbols: list[str]) -> dict[str, Any]:
        """Get real-time quotes for a list of symbols."""
        if settings.mock_schwab:
            return _mock_quotes(symbols)

        await self._rate_limiter.acquire()
        response = await asyncio.to_thread(
            self._client.get_quotes, symbols=symbols
        )
        return response.json()

    async def get_option_chain(
        self,
        symbol: str,
        min_dte: int = 20,
        max_dte: int = 60,
        contract_type: str = "PUT",
    ) -> dict[str, Any]:
        """Fetch option chain for a symbol."""
        if settings.mock_schwab:
            return _mock_option_chain(symbol, min_dte, max_dte, contract_type)

        import schwab
        await self._rate_limiter.acquire()
        if contract_type == "CALL":
            schwab_contract_type = schwab.client.Client.Options.ContractType.CALL
        else:
            schwab_contract_type = schwab.client.Client.Options.ContractType.PUT
        response = await asyncio.to_thread(
            self._client.get_option_chain,
            symbol=symbol,
            contract_type=schwab_contract_type,
            from_date=date.today(),
            to_date=None,
            strike_range=schwab.client.Client.Options.StrikeRange.OUT_OF_THE_MONEY,
        )
        return response.json()

    async def place_order(self, order_spec: Any) -> dict[str, Any]:
        """Place an order and return the Schwab order ID."""
        if settings.mock_schwab:
            import uuid
            mock_id = str(int(uuid.uuid4().int % 1_000_000_000))
            logger.info("MOCK: place_order", order_spec=str(order_spec)[:200], schwab_order_id=mock_id)
            return {"orderId": mock_id, "status": "WORKING"}

        await self._rate_limiter.acquire()
        response = await asyncio.to_thread(
            self._client.place_order, self.account_hash, order_spec
        )
        # schwab-py returns 201 with Location header containing order ID
        location = response.headers.get("Location", "")
        order_id = location.split("/")[-1] if location else ""
        return {"orderId": order_id, "status": "WORKING"}

    async def get_order(self, schwab_order_id: str) -> dict[str, Any]:
        """Get the current status of an order."""
        if settings.mock_schwab:
            return _mock_order_status(schwab_order_id)

        await self._rate_limiter.acquire()
        response = await asyncio.to_thread(
            self._client.get_order, int(schwab_order_id), self.account_hash
        )
        return response.json()

    async def cancel_order(self, schwab_order_id: str) -> bool:
        """Cancel a working order. Returns True if successful."""
        if settings.mock_schwab:
            logger.info("MOCK: cancel_order", schwab_order_id=schwab_order_id)
            return True

        await self._rate_limiter.acquire()
        response = await asyncio.to_thread(
            self._client.cancel_order, int(schwab_order_id), self.account_hash
        )
        return response.status_code in (200, 204)

    async def get_account(self) -> dict[str, Any]:
        """Get account balances and positions."""
        if settings.mock_schwab:
            return _mock_account()

        import schwab
        await self._rate_limiter.acquire()
        response = await asyncio.to_thread(
            self._client.get_account,
            self.account_hash,
            fields=[schwab.client.Client.Account.Fields.POSITIONS],
        )
        return response.json()

    async def get_price_history(self, symbol: str, period_type: str = "year", period: int = 1) -> dict[str, Any]:
        """Get daily OHLCV history for IV rank calculation."""
        if settings.mock_schwab:
            return {"candles": [], "symbol": symbol}

        import schwab
        await self._rate_limiter.acquire()
        response = await asyncio.to_thread(
            self._client.get_price_history_every_day,
            symbol=symbol,
            period_type=schwab.client.Client.PriceHistory.PeriodType.YEAR,
            period=schwab.client.Client.PriceHistory.Period.ONE_YEAR,
        )
        return response.json()


# ── Mock helpers ──────────────────────────────────────────────────────────────

def _mock_quotes(symbols: list[str]) -> dict[str, Any]:
    result = {}
    prices = {"TSLA": 351.0, "IREN": 8.50, "HIM": 4.20, "AAPL": 205.0, "NVDA": 875.0}
    opens = {"TSLA": 365.0, "IREN": 8.80, "HIM": 4.40, "AAPL": 210.0, "NVDA": 900.0}
    for sym in symbols:
        price = prices.get(sym, 100.0)
        open_price = opens.get(sym, price * 1.04)
        result[sym] = {
            "quote": {
                "lastPrice": price,
                "openPrice": open_price,
                "bidPrice": price - 0.05,
                "askPrice": price + 0.05,
                "mark": price,
            }
        }
    return result


def _mock_option_chain(symbol: str, min_dte: int, max_dte: int, contract_type: str = "PUT") -> dict[str, Any]:
    """Return a minimal mock option chain for testing."""
    from datetime import timedelta

    prices = {"TSLA": 351.0, "IREN": 8.50, "HIM": 4.20, "AAPL": 205.0, "NVDA": 875.0}
    stock_price = prices.get(symbol, 100.0)

    # Create one expiration at ~35 DTE
    expiry = date.today() + timedelta(days=35)
    expiry_str = expiry.strftime("%Y-%m-%d")
    dte = 35
    exp_key = f"{expiry_str}:{dte}"

    result: dict[str, Any] = {
        "symbol": symbol,
        "status": "SUCCESS",
        "underlying": {
            "symbol": symbol,
            "mark": stock_price,
            "last": stock_price,
            "open": stock_price * 1.04,
        },
    }

    if contract_type == "CALL":
        # Create a few OTM call strikes (above stock price)
        call_exp_date_map = {}
        strikes = {}
        for pct_otm in [1.05, 1.08, 1.11, 1.14]:
            strike = round(stock_price * pct_otm, 0)
            # Premium roughly 1-2% of stock price, decreasing as strike moves further OTM
            premium = round(stock_price * 0.016 * (1 - (strike - stock_price) / stock_price * 2), 2)
            premium = max(0.50, premium)
            option_symbol = f"{symbol}_{expiry_str[2:].replace('-', '')}C{int(strike)}"
            strikes[str(strike)] = [{
                "putCall": "CALL",
                "symbol": option_symbol,
                "description": f"{symbol} {expiry_str} {strike}C",
                "bid": premium - 0.05,
                "ask": premium + 0.05,
                "mark": premium,
                "last": premium,
                "delta": round(0.25 * (stock_price / strike), 3),
                "gamma": 0.005,
                "theta": -0.03,
                "vega": 0.10,
                "volatility": 65.0,
                "strikePrice": strike,
                "expirationDate": expiry_str,
                "daysToExpiration": dte,
                "openInterest": 1200,
                "totalVolume": 450,
            }]
        call_exp_date_map[exp_key] = strikes
        result["callExpDateMap"] = call_exp_date_map
    else:
        # Create a few OTM put strikes (below stock price)
        put_exp_date_map = {}
        strikes = {}
        for pct_otm in [0.85, 0.88, 0.91, 0.94]:
            strike = round(stock_price * pct_otm, 0)
            # Premium roughly 1-2% of stock price
            premium = round(stock_price * 0.016 * (1 - (stock_price - strike) / stock_price * 2), 2)
            premium = max(0.50, premium)
            option_symbol = f"{symbol}_{expiry_str[2:].replace('-', '')}P{int(strike)}"
            strikes[str(strike)] = [{
                "putCall": "PUT",
                "symbol": option_symbol,
                "description": f"{symbol} {expiry_str} {strike}P",
                "bid": premium - 0.05,
                "ask": premium + 0.05,
                "mark": premium,
                "last": premium,
                "delta": round(-0.25 * (strike / stock_price), 3),
                "gamma": 0.005,
                "theta": -0.03,
                "vega": 0.10,
                "volatility": 65.0,
                "strikePrice": strike,
                "expirationDate": expiry_str,
                "daysToExpiration": dte,
                "openInterest": 1200,
                "totalVolume": 450,
            }]
        put_exp_date_map[exp_key] = strikes
        result["putExpDateMap"] = put_exp_date_map

    return result


def _mock_order_status(schwab_order_id: str) -> dict[str, Any]:
    return {
        "orderId": int(schwab_order_id) if schwab_order_id.isdigit() else 0,
        "status": "FILLED",
        "price": 6.00,
        "filledQuantity": 1,
    }


def _mock_account() -> dict[str, Any]:
    return {
        "securitiesAccount": {
            "currentBalances": {
                "liquidationValue": 52340.0,
                "buyingPower": 24200.0,
                "cashBalance": 10000.0,
            },
            "positions": [
                {
                    "instrument": {"symbol": "TSLA", "assetType": "EQUITY", "description": "Tesla Inc."},
                    "longQuantity": 10,
                    "shortQuantity": 0,
                    "marketValue": 3510.0,
                    "averagePrice": 320.0,
                    "currentDayProfitLossPercentage": 2.1,
                },
                {
                    "instrument": {"symbol": "IREN", "assetType": "EQUITY", "description": "Iris Energy Ltd."},
                    "longQuantity": 500,
                    "shortQuantity": 0,
                    "marketValue": 4250.0,
                    "averagePrice": 9.10,
                    "currentDayProfitLossPercentage": -1.3,
                },
                {
                    "instrument": {"symbol": "NVDA", "assetType": "EQUITY", "description": "NVIDIA Corp."},
                    "longQuantity": 5,
                    "shortQuantity": 0,
                    "marketValue": 4375.0,
                    "averagePrice": 850.0,
                    "currentDayProfitLossPercentage": 0.8,
                },
                {
                    "instrument": {
                        "symbol": "TSLA_250515P310",
                        "assetType": "OPTION",
                        "description": "TSLA May 15 2025 $310 Put",
                        "putCall": "PUT",
                        "strikePrice": 310.0,
                        "expirationDate": "2025-05-15",
                    },
                    "longQuantity": 0,
                    "shortQuantity": 1,
                    "marketValue": -180.0,
                    "averagePrice": 6.00,
                    "currentDayProfitLossPercentage": 0.0,
                },
                {
                    "instrument": {
                        "symbol": "IREN_250515P7",
                        "assetType": "OPTION",
                        "description": "IREN May 15 2025 $7 Put",
                        "putCall": "PUT",
                        "strikePrice": 7.0,
                        "expirationDate": "2025-05-15",
                    },
                    "longQuantity": 0,
                    "shortQuantity": 5,
                    "marketValue": -49.0,
                    "averagePrice": 0.17,
                    "currentDayProfitLossPercentage": 0.0,
                },
            ],
        }
    }


# Singleton instance
schwab_client = SchwabClient()
