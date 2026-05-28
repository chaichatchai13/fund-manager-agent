"""
Pure evaluation functions — no I/O, trivially unit-testable.
Each returns True if the candidate passes the check.
"""
from app.schwab.option_chain import OptionCandidate


def check_dte(candidate: OptionCandidate, min_dte: int, max_dte: int) -> bool:
    return min_dte <= candidate.dte <= max_dte


def check_premium_pct(
    candidate: OptionCandidate,
    min_premium_pct: float,
    max_premium_pct: float | None = None,
) -> bool:
    if candidate.stock_price <= 0:
        return False
    pct = (candidate.mid / candidate.stock_price) * 100
    if pct < min_premium_pct:
        return False
    if max_premium_pct is not None and pct > max_premium_pct:
        return False
    return True


def check_otm_put(candidate: OptionCandidate) -> bool:
    """Put must be out-of-the-money (strike < stock price)."""
    return candidate.strike < candidate.stock_price


# Backwards-compatible alias
def check_otm(candidate: OptionCandidate) -> bool:
    """Put must be out-of-the-money (strike < stock price). Alias for check_otm_put."""
    return check_otm_put(candidate)


def check_otm_call(candidate: OptionCandidate) -> bool:
    """Call must be out-of-the-money (strike > stock price)."""
    return candidate.strike > candidate.stock_price


def check_delta(
    candidate: OptionCandidate,
    min_delta: float | None,
    max_delta: float | None,
) -> bool:
    if min_delta is None and max_delta is None:
        return True
    abs_delta = abs(candidate.delta)
    if min_delta is not None and abs_delta < min_delta:
        return False
    if max_delta is not None and abs_delta > max_delta:
        return False
    return True


def check_iv_rank(candidate: OptionCandidate, min_iv_rank: float | None) -> bool:
    if min_iv_rank is None:
        return True
    return candidate.iv_rank >= min_iv_rank


def check_daily_drop(
    current_price: float,
    open_price: float,
    min_drop_pct: float | None,
    max_drop_pct: float | None,
) -> bool:
    """Check if the stock has dropped the required % from today's open."""
    if min_drop_pct is None and max_drop_pct is None:
        return True
    if open_price <= 0:
        return True
    drop_pct = (open_price - current_price) / open_price * 100
    if min_drop_pct is not None and drop_pct < min_drop_pct:
        return False
    if max_drop_pct is not None and drop_pct > max_drop_pct:
        return False
    return True


def score_candidate(candidate: OptionCandidate, strategy_type: str = "SELL_PUT") -> float:
    """
    Score a candidate for selection (higher = better).

    SELL_PUT: prefer the LOWEST strike (farthest OTM / most protection) that still
              meets the min-premium filter.  Among ties, prefer higher premium.
              Rationale: go as far from the stock price as possible while still
              collecting the required premium.

    SELL_COVERED_CALL: prefer the HIGHEST strike (farthest OTM / least assignment risk)
                       that still meets the min-premium filter.  Among ties, prefer
                       higher premium.
    """
    if strategy_type == "SELL_COVERED_CALL":
        # Higher strike = more OTM = better for covered calls
        return candidate.strike * 1000 + candidate.mid
    # Lower strike = more OTM = better for sell puts
    return (-candidate.strike) * 1000 + candidate.mid
