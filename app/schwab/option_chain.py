"""
Option chain fetcher and parser.
Converts raw Schwab option chain JSON into flat OptionCandidate dataclasses.
"""
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class OptionCandidate:
    symbol: str           # OCC-style option symbol
    underlying: str
    strike: float
    expiration: date
    dte: int
    bid: float
    ask: float
    mid: float
    delta: float
    gamma: float
    theta: float
    vega: float
    iv: float             # implied volatility %
    iv_rank: float        # 0–100, computed separately
    open_interest: int
    volume: int
    stock_price: float    # underlying mark price at time of chain fetch
    put_call: str = "PUT" # "PUT" or "CALL"


def parse_option_chain(
    raw: dict[str, Any],
    iv_rank: float = 0.0,
    contract_type: str = "PUT",
) -> list[OptionCandidate]:
    """
    Parse a raw Schwab option chain response into a flat list of OptionCandidates.
    iv_rank is injected from the IVRankTracker (computed separately).
    contract_type: "PUT" parses putExpDateMap (OTM: strike < stock_price),
                   "CALL" parses callExpDateMap (OTM: strike > stock_price).
    """
    candidates: list[OptionCandidate] = []
    underlying = raw.get("symbol", "")
    underlying_data = raw.get("underlying") or {}
    # Real Schwab API may use "mark", "last", or "underlyingPrice" at top level
    stock_price = float(
        underlying_data.get("mark")
        or underlying_data.get("last")
        or raw.get("underlyingPrice")
        or 0.0
    )

    if contract_type == "CALL":
        exp_date_map = raw.get("callExpDateMap", {})
    else:
        exp_date_map = raw.get("putExpDateMap", {})

    for exp_key, strikes_map in exp_date_map.items():
        # exp_key format: "2025-05-15:35" (date:dte)
        parts = exp_key.split(":")
        try:
            expiration = datetime.strptime(parts[0], "%Y-%m-%d").date()
            dte = int(parts[1])
        except (ValueError, IndexError):
            continue

        for strike_str, options in strikes_map.items():
            if not options:
                continue
            opt = options[0]  # first option in the list (standard single option)
            strike = float(opt.get("strikePrice", strike_str))

            if contract_type == "CALL":
                # Only process OTM calls (strike > stock price)
                if strike <= stock_price:
                    continue
            else:
                # Only process OTM puts (strike < stock price)
                if strike >= stock_price:
                    continue

            bid = float(opt.get("bid") or 0.0)
            ask = float(opt.get("ask") or 0.0)
            mid = float(opt.get("mark") or ((bid + ask) / 2 if bid and ask else 0.0))

            candidates.append(OptionCandidate(
                symbol=opt.get("symbol", ""),
                underlying=underlying,
                strike=strike,
                expiration=expiration,
                dte=dte,
                bid=bid,
                ask=ask,
                mid=mid,
                delta=float(opt.get("delta") or 0.0),
                gamma=float(opt.get("gamma") or 0.0),
                theta=float(opt.get("theta") or 0.0),
                vega=float(opt.get("vega") or 0.0),
                iv=float(opt.get("volatility") or 0.0),
                iv_rank=iv_rank,
                open_interest=int(opt.get("openInterest") or 0),
                volume=int(opt.get("totalVolume") or 0),
                stock_price=stock_price,
                put_call=contract_type,
            ))

    return candidates
