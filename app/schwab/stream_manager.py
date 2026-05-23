"""
StreamManager: manages the Schwab WebSocket streaming connection.
Maintains a price_cache dict updated in real-time.
Publishes price updates to an asyncio.Queue consumed by the WebSocket API.
"""
import asyncio

import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class StreamManager:
    def __init__(self) -> None:
        self.price_cache: dict[str, float] = {}
        self.update_queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        self._stream_client = None
        self._stream_task: asyncio.Task | None = None
        self._subscribed_symbols: set[str] = set()

    async def start(self) -> None:
        if settings.mock_schwab:
            logger.info("Mock mode — stream manager not started")
            return
        self._stream_task = asyncio.create_task(self._run_stream())
        logger.info("Stream manager started")

    async def stop(self) -> None:
        if self._stream_task:
            self._stream_task.cancel()
        if self._stream_client:
            try:
                await self._stream_client.logout()
            except Exception:
                pass
        logger.info("Stream manager stopped")

    async def subscribe(self, option_symbols: list[str]) -> None:
        """Subscribe to live quotes for a list of option symbols."""
        new_symbols = set(option_symbols) - self._subscribed_symbols
        if not new_symbols:
            return

        self._subscribed_symbols.update(new_symbols)

        if self._stream_client and not settings.mock_schwab:
            try:
                import schwab.streaming
                await self._stream_client.level_one_option_subs(
                    list(self._subscribed_symbols),
                    fields=schwab.streaming.StreamClient.LevelOneOption.Field.all_fields(),
                )
                logger.info("Subscribed to option quotes", symbols=list(new_symbols))
            except Exception as exc:
                logger.warning("Failed to subscribe to option stream", error=str(exc))

    async def unsubscribe(self, option_symbols: list[str]) -> None:
        for sym in option_symbols:
            self._subscribed_symbols.discard(sym)

    async def _run_stream(self) -> None:
        """Main streaming loop with reconnect on failure."""
        from tenacity import retry, stop_never, wait_exponential

        while True:
            try:
                await self._connect_and_stream()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Stream disconnected — reconnecting in 10s", error=str(exc))
                await asyncio.sleep(10)

    async def _connect_and_stream(self) -> None:
        import schwab.streaming
        from app.schwab.client import schwab_client as sc

        if not sc._client:
            logger.warning("Schwab client not initialized — skipping stream")
            return

        # schwab-py v1.x: StreamClient is created directly from the authenticated client
        self._stream_client = schwab.streaming.StreamClient(sc._client)
        await self._stream_client.login()
        logger.info("Stream client connected")

        if self._subscribed_symbols:
            await self._stream_client.level_one_option_subs(
                list(self._subscribed_symbols),
                fields=schwab.streaming.StreamClient.LevelOneOption.Field.all_fields(),
            )

        async def handle_option_quote(msg: dict) -> None:
            content = msg.get("content", [])
            for item in content:
                symbol = item.get("key") or item.get("symbol")
                # Field 3 = mark price in Level One Options stream
                mark = item.get(
                    schwab.streaming.StreamClient.LevelOneOption.Field.MARK, item.get("3")
                )
                if symbol and mark is not None:
                    price = float(mark)
                    self.price_cache[symbol] = price
                    # Fire price alerts (non-blocking)
                    try:
                        from app.services.alert_service import alert_service
                        asyncio.create_task(alert_service.check_price(symbol, price))
                    except Exception:
                        pass
                    try:
                        self.update_queue.put_nowait({
                            "type": "price_update",
                            "symbol": symbol,
                            "price": price,
                        })
                    except asyncio.QueueFull:
                        pass  # consumers are slow, drop update

        self._stream_client.add_level_one_option_handler(handle_option_quote)
        await self._stream_client.handle_message()


# Singleton
stream_manager = StreamManager()
