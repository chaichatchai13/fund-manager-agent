"""
Build Schwab option orders using schwab-py's order builder.
"""
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def build_sell_to_open_limit(option_symbol: str, quantity: int, limit_price: float) -> Any:
    """
    Build a sell-to-open limit order for a put option.
    limit_price is the credit per contract (e.g. 6.00).
    """
    import schwab.orders.options as opt
    import schwab.orders.common as common

    order = (
        opt.option_sell_to_open_limit(option_symbol, quantity, f"{float(limit_price):.2f}")
        .set_duration(common.Duration.DAY)
        .set_session(common.Session.NORMAL)
        .build()
    )
    return order


def build_buy_to_close_limit(
    option_symbol: str, quantity: int, limit_price: float, gtc: bool = False
) -> Any:
    """
    Build a buy-to-close limit order for a put option.
    limit_price is the debit per contract (e.g. 1.50).
    gtc=True sets the order as Good Until Cancelled.
    """
    import schwab.orders.options as opt
    import schwab.orders.common as common

    duration = common.Duration.GOOD_TILL_CANCEL if gtc else common.Duration.DAY
    order = (
        opt.option_buy_to_close_limit(option_symbol, quantity, f"{float(limit_price):.2f}")
        .set_duration(duration)
        .set_session(common.Session.NORMAL)
        .build()
    )
    return order


def build_buy_to_close_market(option_symbol: str, quantity: int) -> Any:
    """
    Build a buy-to-close market order (for stop-loss scenarios).
    """
    import schwab.orders.options as opt
    import schwab.orders.common as common

    order = (
        opt.option_buy_to_close_market(option_symbol, quantity)
        .set_duration(common.Duration.DAY)
        .set_session(common.Session.NORMAL)
        .build()
    )
    return order
