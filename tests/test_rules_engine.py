"""Unit tests for rules engine evaluators."""
from datetime import date, timedelta

import pytest

from app.rules.evaluators import (
    check_daily_drop,
    check_delta,
    check_dte,
    check_iv_rank,
    check_otm,
    check_premium_pct,
    score_candidate,
)
from app.schwab.option_chain import OptionCandidate


def make_candidate(
    strike=300.0,
    stock_price=351.0,
    dte=35,
    mid=6.0,
    delta=-0.25,
    iv_rank=55.0,
) -> OptionCandidate:
    return OptionCandidate(
        symbol="TSLA_250515P310",
        underlying="TSLA",
        strike=strike,
        expiration=date.today() + timedelta(days=dte),
        dte=dte,
        bid=mid - 0.05,
        ask=mid + 0.05,
        mid=mid,
        delta=delta,
        gamma=0.005,
        theta=-0.03,
        vega=0.10,
        iv=65.0,
        iv_rank=iv_rank,
        open_interest=1200,
        volume=450,
        stock_price=stock_price,
    )


def test_check_dte_pass():
    c = make_candidate(dte=35)
    assert check_dte(c, 30, 45) is True


def test_check_dte_too_low():
    c = make_candidate(dte=20)
    assert check_dte(c, 30, 45) is False


def test_check_dte_too_high():
    c = make_candidate(dte=50)
    assert check_dte(c, 30, 45) is False


def test_check_premium_pct_pass():
    # $6.00 / $351.00 = 1.71% — should pass 1.0% min
    c = make_candidate(mid=6.0, stock_price=351.0)
    assert check_premium_pct(c, min_premium_pct=1.0) is True


def test_check_premium_pct_fail():
    # $2.00 / $351.00 = 0.57% — should fail 1.0% min
    c = make_candidate(mid=2.0, stock_price=351.0)
    assert check_premium_pct(c, min_premium_pct=1.0) is False


def test_check_premium_pct_max_bound():
    # $8.00 / $351.00 = 2.28% — should fail 2.0% max
    c = make_candidate(mid=8.0, stock_price=351.0)
    assert check_premium_pct(c, min_premium_pct=1.0, max_premium_pct=2.0) is False


def test_check_otm_pass():
    c = make_candidate(strike=310.0, stock_price=351.0)
    assert check_otm(c) is True


def test_check_otm_fail_itm():
    c = make_candidate(strike=360.0, stock_price=351.0)
    assert check_otm(c) is False


def test_check_delta_no_filter():
    c = make_candidate(delta=-0.25)
    assert check_delta(c, None, None) is True


def test_check_delta_pass():
    c = make_candidate(delta=-0.25)
    assert check_delta(c, min_delta=0.20, max_delta=0.35) is True


def test_check_delta_fail_too_high():
    c = make_candidate(delta=-0.45)
    assert check_delta(c, min_delta=0.20, max_delta=0.35) is False


def test_check_iv_rank_pass():
    c = make_candidate(iv_rank=60.0)
    assert check_iv_rank(c, min_iv_rank=50.0) is True


def test_check_iv_rank_fail():
    c = make_candidate(iv_rank=40.0)
    assert check_iv_rank(c, min_iv_rank=50.0) is False


def test_check_iv_rank_no_filter():
    c = make_candidate(iv_rank=10.0)
    assert check_iv_rank(c, min_iv_rank=None) is True


def test_check_daily_drop_no_filter():
    assert check_daily_drop(100.0, 105.0, None, None) is True


def test_check_daily_drop_pass():
    # 5% drop: (105 - 99.75) / 105 = 5%
    assert check_daily_drop(99.75, 105.0, min_drop_pct=3.0, max_drop_pct=10.0) is True


def test_check_daily_drop_not_enough():
    # 1% drop — needs 3%
    assert check_daily_drop(103.95, 105.0, min_drop_pct=3.0, max_drop_pct=10.0) is False


def test_check_daily_drop_too_much():
    # 12% drop — over 10% max
    assert check_daily_drop(92.4, 105.0, min_drop_pct=3.0, max_drop_pct=10.0) is False


def test_score_higher_strike_wins():
    c_low = make_candidate(strike=290.0, mid=4.0)
    c_high = make_candidate(strike=310.0, mid=6.0)
    assert score_candidate(c_high) > score_candidate(c_low)
